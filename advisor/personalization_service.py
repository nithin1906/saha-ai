# advisor/personalization_service.py

def personalize_signal(ml_signal, avg_buy_price, current_price, num_shares):
    """
    Refines a generic ML signal with advanced position sizing advice using a first-person persona.
    """
    profit_loss_percent = (current_price - avg_buy_price) / avg_buy_price
    initial_investment = avg_buy_price * num_shares
    current_value = current_price * num_shares

    # --- Rule: Catastrophic Loss Override ---
    if profit_loss_percent < -0.20:
        if ml_signal == 'BUY':
            return 'HOLD (Caution)', f"My analysis suggests a potential 'BUY', but your position is down {profit_loss_percent:.2%}. To avoid high risk, I recommend you 'HOLD' and wait for a stronger recovery signal before considering averaging down."
        if ml_signal == 'SELL':
             return 'Strong Sell', f"My analysis confirms a 'SELL' signal and you are down {profit_loss_percent:.2%}. I strongly recommend you exit your entire position of {num_shares} shares to prevent further losses."

    # --- Rule: Profit Taking ---
    if ml_signal == 'BUY' and profit_loss_percent > 0.25:
        shares_to_sell = int(num_shares * 0.25) # Suggest selling 25%
        if shares_to_sell < 1:
            return 'HOLD (Lock in Profits)', f"You are up {profit_loss_percent:.2%}, which is a significant gain. As your holding is small, I suggest holding for now, but be prepared to sell to lock in your profit."
        profit_to_book = shares_to_sell * (current_price - avg_buy_price)
        return f'SELL {shares_to_sell} SHARES (Book Profit)', f"You are up {profit_loss_percent:.2%}, which is a significant gain. To secure your profits, my advice is to sell {shares_to_sell} shares (25% of your holding) to book a profit of roughly ₹{profit_to_book:,.2f}."

    # --- Rule: Averaging Down ---
    if ml_signal == 'BUY' and -0.20 < profit_loss_percent < -0.05:
        shares_to_add = int(num_shares * 0.20) # Suggest adding 20%
        if shares_to_add < 1:
            return 'HOLD', f"I see a potential buying opportunity. Since your current holding is small, I recommend you 'HOLD' for now and monitor the stock's performance."
        new_total_shares = num_shares + shares_to_add
        new_investment = shares_to_add * current_price
        new_avg_price = (initial_investment + new_investment) / new_total_shares
        return f'BUY {shares_to_add} MORE SHARES (Average Down)', f"I see a potential buying opportunity. By purchasing {shares_to_add} more shares at the current price, you can lower your average buy price from ₹{avg_buy_price:,.2f} to approximately ₹{new_avg_price:,.2f}, improving your break-even point."

    # --- Rule: Minor Loss Management ---
    if ml_signal == 'SELL' and profit_loss_percent > -0.10:
        shares_to_sell = int(num_shares * 0.5) # Suggest selling half
        if shares_to_sell < 1:
            return 'HOLD', f"My analysis suggests a 'SELL', but your loss is minor ({profit_loss_percent:.2%}). Given your small position, it's best to 'HOLD' and wait for a clearer signal."
        return f'SELL {shares_to_sell} SHARES (Reduce Risk)', f"My analysis suggests a 'SELL', but your loss is minor ({profit_loss_percent:.2%}). To reduce your risk without exiting completely, consider selling half your position ({shares_to_sell} shares)."

    # --- Default Cases (UPDATED) ---
    if ml_signal == 'HOLD':
        return 'HOLD', f"My analysis suggests 'HOLD'. You are currently at a {profit_loss_percent:.2%} profit/loss. I don't recommend any action for your {num_shares} shares at this time."
    
    if ml_signal == 'BUY':
        return 'Strong Buy', f"My primary signal is a 'Strong Buy'. Based on a combination of technical, fundamental, and sentiment data, I recommend considering an entry or adding to your position."
    
    if ml_signal == 'SELL':
        return 'Strong Sell', f"My primary signal is a 'Strong Sell' for your entire position of {num_shares} shares. This is based on a combination of technical, fundamental, and sentiment data."

    # Fallback just in case
    return ml_signal, "My analysis is based on current technical indicators."