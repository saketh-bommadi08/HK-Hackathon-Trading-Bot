def should_exit(position, entry_price, current_price, signal):
    try:
        position = float(position)
        entry_price = float(entry_price)
        current_price = float(current_price)
    except (TypeError, ValueError):
        return False

    if position <= 0 or entry_price <= 0 or current_price <= 0:
        return False

    if signal == "SELL":
        return True

    if current_price <= entry_price * 0.99:
        return True

    return False
