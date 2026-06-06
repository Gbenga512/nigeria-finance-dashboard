from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import MetaTrader5 as mt5


# ============================================================
# REAL MT5 LIVE TRADING BOT - ONE FILE
# ============================================================
#
# Requirements:
#   pip install MetaTrader5
#
# MT5 terminal requirements:
#   1. MetaTrader 5 desktop terminal installed and opened.
#   2. Logged into your broker account, or provide env login details.
#   3. Algo Trading enabled in MT5.
#   4. Symbol visible in Market Watch.
#
# Run dry check mode:
#   python event_trader_single_file.py --symbols EURUSD GBPUSD
#
# Run REAL live trading:
#   python event_trader_single_file.py --symbols EURUSD GBPUSD --live
#
# Optional env login:
#   MT5_LOGIN=123456
#   MT5_PASSWORD=your_password
#   MT5_SERVER=YourBroker-Server
#   MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
#
# This is real execution code. It can lose real money.
# Use demo first and understand every setting before live use.


LOG = logging.getLogger("mt5-live-trader")
STATE_FILE = Path(__file__).with_suffix(".state.json")


@dataclass(frozen=True)
class StrategySettings:
    min_move_pips: float = 3.0
    take_profit_pips: float = 10.0
    stop_loss_pips: float = 6.0
    lot: float = 0.01
    max_spread_pips: float = 2.0
    cooldown_seconds: int = 60
    magic: int = 20260529
    deviation_points: int = 20


@dataclass(frozen=True)
class RiskSettings:
    max_daily_trades: int = 5
    max_open_positions: int = 3
    max_symbol_positions: int = 1
    max_pending_orders: int = 1


@dataclass(frozen=True)
class AppSettings:
    strategy: StrategySettings = field(default_factory=StrategySettings)
    risk: RiskSettings = field(default_factory=RiskSettings)


@dataclass
class BotState:
    day: str
    daily_trade_count: int = 0
    last_mid_by_symbol: dict[str, float] = field(default_factory=dict)
    last_trade_time_by_key: dict[str, float] = field(default_factory=dict)
    pending_command_ids: set[str] = field(default_factory=set)

    @classmethod
    def load(cls) -> "BotState":
        today = date.today().isoformat()
        if not STATE_FILE.exists():
            return cls(day=today)

        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if raw.get("day") != today:
                return cls(day=today)
            return cls(
                day=today,
                daily_trade_count=int(raw.get("daily_trade_count", 0)),
                last_mid_by_symbol=dict(raw.get("last_mid_by_symbol", {})),
                last_trade_time_by_key=dict(raw.get("last_trade_time_by_key", {})),
                pending_command_ids=set(raw.get("pending_command_ids", [])),
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            LOG.warning("Could not load state file, starting fresh.")
            return cls(day=today)

    def save(self) -> None:
        data = asdict(self)
        data["pending_command_ids"] = sorted(self.pending_command_ids)
        STATE_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


@dataclass(frozen=True)
class TradeCommand:
    command_id: str
    symbol: str
    side: str
    volume: float
    take_profit_pips: float
    stop_loss_pips: float


def initialize_mt5() -> None:
    path = os.getenv("MT5_PATH")
    login = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")

    if path:
        ok = mt5.initialize(path=path)
    else:
        ok = mt5.initialize()

    if not ok:
        raise RuntimeError(f"mt5.initialize() failed: {mt5.last_error()}")

    if login and password and server:
        if not mt5.login(int(login), password=password, server=server):
            raise RuntimeError(f"mt5.login() failed: {mt5.last_error()}")

    terminal = mt5.terminal_info()
    account = mt5.account_info()
    if terminal is None:
        raise RuntimeError(f"terminal_info() failed: {mt5.last_error()}")
    if account is None:
        raise RuntimeError(f"account_info() failed: {mt5.last_error()}")
    if not terminal.trade_allowed:
        raise RuntimeError("MT5 terminal says trading is not allowed. Enable Algo Trading in MetaTrader 5.")
    if not account.trade_allowed:
        raise RuntimeError("Account says trading is not allowed.")

    LOG.info("Connected to MT5 account=%s server=%s balance=%s", account.login, account.server, account.balance)


def shutdown_mt5() -> None:
    mt5.shutdown()


def ensure_symbol(symbol: str) -> Any:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"symbol_info({symbol}) failed: {mt5.last_error()}")
    if not info.visible and not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"symbol_select({symbol}) failed: {mt5.last_error()}")
    return mt5.symbol_info(symbol)


def pip_size(symbol_info: Any) -> float:
    if symbol_info.digits in (3, 5):
        return symbol_info.point * 10
    return symbol_info.point


def pips_to_price(symbol_info: Any, pips: float) -> float:
    return pips * pip_size(symbol_info)


def normalize_price(symbol_info: Any, price: float) -> float:
    return round(price, symbol_info.digits)


def spread_pips(symbol: str, symbol_info: Any) -> float:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"symbol_info_tick({symbol}) failed: {mt5.last_error()}")
    return (tick.ask - tick.bid) / pip_size(symbol_info)


def min_stop_distance_price(symbol_info: Any) -> float:
    stops_level = getattr(symbol_info, "trade_stops_level", 0) or getattr(symbol_info, "stops_level", 0) or 0
    return stops_level * symbol_info.point


def adjust_sl_tp_for_broker_rules(
    symbol_info: Any,
    *,
    price: float,
    side: str,
    sl: float,
    tp: float,
) -> tuple[float, float]:
    min_dist = min_stop_distance_price(symbol_info)
    if min_dist <= 0:
        return normalize_price(symbol_info, sl), normalize_price(symbol_info, tp)

    if side == "BUY":
        sl = min(sl, price - min_dist)
        tp = max(tp, price + min_dist)
    else:
        sl = max(sl, price + min_dist)
        tp = min(tp, price - min_dist)
    return normalize_price(symbol_info, sl), normalize_price(symbol_info, tp)


def get_positions(symbol: str | None = None, magic: int | None = None) -> list[Any]:
    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if positions is None:
        return []
    if magic is None:
        return list(positions)
    return [position for position in positions if getattr(position, "magic", None) == magic]


def open_position_count(magic: int) -> int:
    return sum(1 for position in get_positions(magic=magic) if abs(position.volume) > 0)


def symbol_position_count(symbol: str, magic: int) -> int:
    return sum(1 for position in get_positions(symbol=symbol, magic=magic) if abs(position.volume) > 0)


def make_command(symbol: str, side: str, settings: StrategySettings) -> TradeCommand:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"symbol_info_tick({symbol}) failed: {mt5.last_error()}")
    command_key = f"{symbol}:{side}:{tick.bid:.10f}:{tick.ask:.10f}:{int(time.time() // settings.cooldown_seconds)}"
    return TradeCommand(
        command_id=str(uuid5(NAMESPACE_URL, command_key)),
        symbol=symbol,
        side=side,
        volume=settings.lot,
        take_profit_pips=settings.take_profit_pips,
        stop_loss_pips=settings.stop_loss_pips,
    )


def validate_trade(command: TradeCommand, state: BotState, settings: AppSettings) -> tuple[bool, str]:
    if command.command_id in state.pending_command_ids:
        return False, "duplicate_pending_command"
    if len(state.pending_command_ids) >= settings.risk.max_pending_orders:
        return False, "too_many_pending_orders"
    if state.daily_trade_count >= settings.risk.max_daily_trades:
        return False, "daily_trade_limit"
    if open_position_count(settings.strategy.magic) >= settings.risk.max_open_positions:
        return False, "open_position_limit"
    if symbol_position_count(command.symbol, settings.strategy.magic) >= settings.risk.max_symbol_positions:
        return False, "symbol_position_limit"

    info = ensure_symbol(command.symbol)
    current_spread = spread_pips(command.symbol, info)
    if current_spread > settings.strategy.max_spread_pips:
        return False, f"spread_too_high:{current_spread:.2f}_pips"

    cooldown_key = f"{command.symbol}:{command.side}"
    last_trade_time = state.last_trade_time_by_key.get(cooldown_key, 0)
    if time.time() - last_trade_time < settings.strategy.cooldown_seconds:
        return False, "cooldown_active"

    return True, "ok"


def build_order_request(command: TradeCommand, settings: StrategySettings) -> dict[str, Any]:
    symbol_info = ensure_symbol(command.symbol)
    tick = mt5.symbol_info_tick(command.symbol)
    if tick is None:
        raise RuntimeError(f"symbol_info_tick({command.symbol}) failed: {mt5.last_error()}")

    is_buy = command.side == "BUY"
    price = tick.ask if is_buy else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    if is_buy:
        sl = price - pips_to_price(symbol_info, command.stop_loss_pips)
        tp = price + pips_to_price(symbol_info, command.take_profit_pips)
    else:
        sl = price + pips_to_price(symbol_info, command.stop_loss_pips)
        tp = price - pips_to_price(symbol_info, command.take_profit_pips)

    sl, tp = adjust_sl_tp_for_broker_rules(symbol_info, price=price, side=command.side, sl=sl, tp=tp)

    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": command.symbol,
        "volume": command.volume,
        "type": order_type,
        "price": normalize_price(symbol_info, price),
        "sl": sl,
        "tp": tp,
        "deviation": settings.deviation_points,
        "magic": settings.magic,
        "comment": command.command_id[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }


def filling_modes_to_try() -> list[int]:
    modes = []
    for name in ("ORDER_FILLING_IOC", "ORDER_FILLING_FOK", "ORDER_FILLING_RETURN"):
        value = getattr(mt5, name, None)
        if value is not None and value not in modes:
            modes.append(value)
    return modes


def check_and_send_order(command: TradeCommand, settings: StrategySettings, *, live: bool) -> tuple[bool, str]:
    base_request = build_order_request(command, settings)
    last_message = "no_filling_mode_attempted"

    for filling_mode in filling_modes_to_try():
        request = dict(base_request)
        request["type_filling"] = filling_mode

        check = mt5.order_check(request)
        if check is None:
            last_message = f"order_check_none:{mt5.last_error()}"
            continue

        check_retcode = getattr(check, "retcode", None)
        check_comment = getattr(check, "comment", "")
        if check_retcode not in (0, mt5.TRADE_RETCODE_DONE):
            last_message = f"order_check_failed:retcode={check_retcode}:comment={check_comment}"
            continue

        if not live:
            LOG.warning("DRY RUN passed order_check. Add --live to send: %s", request)
            return False, "dry_run_order_not_sent"

        result = mt5.order_send(request)
        if result is None:
            last_message = f"order_send_none:{mt5.last_error()}"
            continue

        retcode = getattr(result, "retcode", None)
        comment = getattr(result, "comment", "")
        if retcode == mt5.TRADE_RETCODE_DONE:
            LOG.warning("LIVE TRADE EXECUTED: %s result=%s", request, result)
            return True, "executed"

        last_message = f"order_send_failed:retcode={retcode}:comment={comment}"

    return False, last_message


def strategy_signal(symbol: str, state: BotState, settings: StrategySettings) -> str | None:
    info = ensure_symbol(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"symbol_info_tick({symbol}) failed: {mt5.last_error()}")

    mid = (tick.bid + tick.ask) / 2
    last_mid = state.last_mid_by_symbol.get(symbol)
    state.last_mid_by_symbol[symbol] = mid

    if last_mid is None:
        return None

    move_pips = (mid - last_mid) / pip_size(info)
    if abs(move_pips) < settings.min_move_pips:
        return None

    return "BUY" if move_pips > 0 else "SELL"


def process_symbol(symbol: str, state: BotState, settings: AppSettings, *, live: bool) -> None:
    side = strategy_signal(symbol, state, settings.strategy)
    if side is None:
        return

    command = make_command(symbol, side, settings.strategy)
    allowed, reason = validate_trade(command, state, settings)
    if not allowed:
        LOG.info("%s %s rejected: %s", symbol, side, reason)
        return

    state.pending_command_ids.add(command.command_id)
    state.save()

    try:
        executed, message = check_and_send_order(command, settings.strategy, live=live)
        LOG.info("%s %s result: %s", symbol, side, message)
        if executed:
            state.daily_trade_count += 1
            state.last_trade_time_by_key[f"{symbol}:{side}"] = time.time()
    finally:
        state.pending_command_ids.discard(command.command_id)
        state.save()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real MetaTrader5 live trading bot.")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to trade, e.g. EURUSD GBPUSD USDJPY")
    parser.add_argument("--live", action="store_true", help="Actually send live orders. Without this, only order_check is run.")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    parser.add_argument("--lot", type=float, default=0.01)
    parser.add_argument("--sl-pips", type=float, default=6.0)
    parser.add_argument("--tp-pips", type=float, default=10.0)
    parser.add_argument("--min-move-pips", type=float, default=3.0)
    parser.add_argument("--max-spread-pips", type=float, default=2.0)
    parser.add_argument("--max-daily-trades", type=int, default=5)
    parser.add_argument("--max-open-positions", type=int, default=3)
    parser.add_argument("--max-symbol-positions", type=int, default=1)
    parser.add_argument("--cooldown-seconds", type=int, default=60)
    parser.add_argument("--magic", type=int, default=20260529)
    return parser.parse_args()


def build_settings(args: argparse.Namespace) -> AppSettings:
    return AppSettings(
        strategy=StrategySettings(
            min_move_pips=args.min_move_pips,
            take_profit_pips=args.tp_pips,
            stop_loss_pips=args.sl_pips,
            lot=args.lot,
            max_spread_pips=args.max_spread_pips,
            cooldown_seconds=args.cooldown_seconds,
            magic=args.magic,
        ),
        risk=RiskSettings(
            max_daily_trades=args.max_daily_trades,
            max_open_positions=args.max_open_positions,
            max_symbol_positions=args.max_symbol_positions,
        ),
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args = parse_args()
    settings = build_settings(args)
    state = BotState.load()
    running = True

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    if args.live:
        LOG.warning("LIVE MODE ENABLED. REAL ORDERS CAN BE SENT.")
    else:
        LOG.warning("DRY RUN MODE. order_check() runs, but order_send() is blocked. Use --live for real trades.")

    initialize_mt5()
    try:
        for symbol in args.symbols:
            ensure_symbol(symbol)

        while running:
            for symbol in args.symbols:
                try:
                    process_symbol(symbol, state, settings, live=args.live)
                except Exception as exc:
                    LOG.exception("Error processing %s: %s", symbol, exc)
            time.sleep(args.interval)
    finally:
        state.save()
        shutdown_mt5()


if __name__ == "__main__":
    main()
