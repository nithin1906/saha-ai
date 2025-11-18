import yfinance as yf

def get_portfolio_health(portfolio):
    holdings = portfolio.holdings.all()
    if not holdings:
        return {
            "overall_score": 0,
            "diversification": {"score": 0, "feedback": "Your portfolio is empty. Add holdings to get a score."},
            "risk": {"score": 0, "feedback": "No holdings to analyze risk."},
            "performance": {"score": 0, "feedback": "No performance data available."}
        }

    total_value, sector_concentration, beta_values, performance_data = 0, {}, [], []

    for holding in holdings:
        try:
            stock = yf.Ticker(holding.ticker)
            info = stock.info
            
            current_price = info.get('currentPrice')
            if not current_price: continue # Skip if price is unavailable

            holding_value = float(current_price) * holding.quantity
            total_value += holding_value
            
            sector = info.get('sector', 'Other')
            sector_concentration[sector] = sector_concentration.get(sector, 0) + holding_value
            
            beta = info.get('beta', 1.0)
            if beta is not None: beta_values.append(beta)

            pnl_percent = (float(current_price) - float(holding.average_buy_price)) / float(holding.average_buy_price)
            performance_data.append(pnl_percent)

        except Exception as e:
            print(f"Could not fetch data for {holding.ticker} during health analysis. Skipping. Error: {e}")
            continue

    if total_value == 0:
         return {"overall_score": 0, "diversification": {"score": 0, "feedback": "Could not fetch market data for your holdings."}, "risk": {"score": 0, "feedback": "Could not fetch market data."}, "performance": {"score": 0, "feedback": "Could not fetch market data."}}

    num_sectors = len(sector_concentration)
    max_concentration = max(sector_concentration.values()) / total_value if total_value > 0 else 0
    
    d_score = 10 if num_sectors >= 5 and max_concentration < 0.3 else (7 if num_sectors >= 3 and max_concentration < 0.5 else (2 if max_concentration > 0.7 else 5))
    d_fb = f"Invested in {num_sectors} sectors. Largest is {max_concentration:.1%}."

    avg_beta = sum(beta_values) / len(beta_values) if beta_values else 1.0
    r_score = 9 if avg_beta < 0.8 else (6 if avg_beta < 1.2 else 3)
    r_fb = f"Portfolio beta is {avg_beta:.2f}, indicating its volatility vs. the market."

    avg_perf = sum(performance_data) / len(performance_data) if performance_data else 0
    p_score = 10 if avg_perf > 0.15 else (7 if avg_perf > 0.05 else (2 if avg_perf < -0.10 else 5))
    p_fb = f"Average unrealized gain/loss is {avg_perf:.2%}."

    overall = round((d_score * 0.4) + (r_score * 0.4) + (p_score * 0.2), 1)

    return {
        "overall_score": overall,
        "diversification": {"score": d_score, "feedback": d_fb},
        "risk": {"score": r_score, "feedback": r_fb},
        "performance": {"score": p_score, "feedback": p_fb}
    }

