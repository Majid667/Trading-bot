import logging
from flask import Flask, render_template_string, jsonify
from datetime import datetime
from trading_engine import TradingEngine

logger = logging.getLogger(__name__)

app = Flask(__name__)
trading_engine = None


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/stats")
def get_stats():
    """Get current trading statistics."""
    if not trading_engine:
        return jsonify({"error": "Trading engine not initialized"}), 500

    stats = trading_engine.get_daily_stats()
    stats["open_trades"] = len(trading_engine.open_trades)
    stats["timestamp"] = datetime.now().isoformat()

    return jsonify(stats)


@app.route("/api/trades")
def get_trades():
    """Get all trades."""
    if not trading_engine:
        return jsonify({"error": "Trading engine not initialized"}), 500

    trades = [t.to_dict() for t in trading_engine.trades]
    return jsonify({"trades": trades})


@app.route("/api/open-trades")
def get_open_trades():
    """Get currently open trades."""
    if not trading_engine:
        return jsonify({"error": "Trading engine not initialized"}), 500

    open_trades = [t.to_dict() for t in trading_engine.open_trades.values()]
    return jsonify({"open_trades": open_trades})


def start_dashboard(engine: TradingEngine, host: str = "0.0.0.0", port: int = 5000):
    """Start the dashboard server."""
    global trading_engine
    trading_engine = engine
    logger.info(f"Starting dashboard on {host}:{port}")
    app.run(host=host, port=port, debug=False)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BTC Scalping Bot Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
        }

        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }

        .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.4);
            transform: translateY(-5px);
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-detail {
            font-size: 0.85em;
            opacity: 0.7;
        }

        .positive {
            color: #4ade80;
        }

        .negative {
            color: #f87171;
        }

        .neutral {
            color: #fbbf24;
        }

        .section {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }

        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        th {
            background: rgba(255, 255, 255, 0.1);
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            font-weight: 600;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        .timestamp {
            font-size: 0.9em;
            opacity: 0.6;
            margin-top: 15px;
            text-align: right;
        }

        .loading {
            text-align: center;
            padding: 20px;
            opacity: 0.7;
        }

        .error {
            color: #f87171;
            padding: 15px;
            background: rgba(248, 113, 113, 0.1);
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 BTC Scalping Bot</h1>
            <p class="subtitle">Real-time Trading Dashboard</p>
        </header>

        <div class="stats-grid" id="stats-container">
            <div class="loading">Loading statistics...</div>
        </div>

        <div class="section">
            <h2 class="section-title">Trade History</h2>
            <table id="trades-table">
                <thead>
                    <tr>
                        <th>Trade ID</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>P&L</th>
                        <th>Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr><td colspan="6" class="loading">Loading trades...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="timestamp" id="timestamp">Last updated: -</div>
    </div>

    <script>
        function formatCurrency(value) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(value);
        }

        function formatPercent(value) {
            const color = value >= 0 ? 'positive' : 'negative';
            return `<span class="${color}">${value.toFixed(2)}%</span>`;
        }

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    const html = `
                        <div class="stat-card">
                            <div class="stat-label">Current Balance</div>
                            <div class="stat-value ${data.current_balance >= 100 ? 'positive' : 'negative'}">
                                ${formatCurrency(data.current_balance)}
                            </div>
                            <div class="stat-detail">Started with ${formatCurrency(100)}</div>
                        </div>

                        <div class="stat-card">
                            <div class="stat-label">Total Trades</div>
                            <div class="stat-value">${data.total_trades}</div>
                            <div class="stat-detail">
                                ✓ ${data.winning_trades} | ✗ ${data.losing_trades}
                            </div>
                        </div>

                        <div class="stat-card">
                            <div class="stat-label">Losing Trades Today</div>
                            <div class="stat-value ${data.daily_losing_trades >= 3 ? 'negative' : 'positive'}">
                                ${data.daily_losing_trades}/${data.max_losing_trades_allowed}
                            </div>
                            <div class="stat-detail">
                                ${data.trading_stopped ? '🛑 Trading Stopped' : '🟢 Trading Active'}
                            </div>
                        </div>

                        <div class="stat-card">
                            <div class="stat-label">Win Rate</div>
                            <div class="stat-value">${data.win_rate.toFixed(1)}%</div>
                            <div class="stat-detail">
                                ${data.open_trades} open position(s)
                            </div>
                        </div>

                        <div class="stat-card">
                            <div class="stat-label">Total P&L</div>
                            <div class="stat-value ${data.total_profit >= 0 ? 'positive' : 'negative'}">
                                ${formatCurrency(data.total_profit)}
                            </div>
                            <div class="stat-detail">
                                ROI: ${formatPercent(data.roi_percent).replace('<span class="positive">', '').replace('<span class="negative">', '').replace('</span>', '')}
                            </div>
                        </div>
                    `;
                    document.getElementById('stats-container').innerHTML = html;
                    document.getElementById('timestamp').innerText =
                        'Last updated: ' + new Date(data.timestamp).toLocaleTimeString();
                })
                .catch(e => {
                    document.getElementById('stats-container').innerHTML =
                        '<div class="error">Failed to load statistics</div>';
                });
        }

        function updateTrades() {
            fetch('/api/trades')
                .then(r => r.json())
                .then(data => {
                    const tbody = document.getElementById('trades-body');
                    if (data.trades.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="loading">No trades yet</td></tr>';
                        return;
                    }

                    tbody.innerHTML = data.trades.map(t => `
                        <tr>
                            <td>${t.trade_id}</td>
                            <td>${formatCurrency(t.entry_price)}</td>
                            <td>${t.exit_price ? formatCurrency(t.exit_price) : '-'}</td>
                            <td class="${t.profit_loss >= 0 ? 'positive' : 'negative'}">
                                ${formatCurrency(t.profit_loss)}
                            </td>
                            <td>${t.duration_seconds}s</td>
                            <td>${t.state}</td>
                        </tr>
                    `).join('');
                })
                .catch(e => {
                    document.getElementById('trades-body').innerHTML =
                        '<tr><td colspan="6" class="error">Failed to load trades</td></tr>';
                });
        }

        updateStats();
        updateTrades();
        setInterval(updateStats, 2000);
        setInterval(updateTrades, 5000);
    </script>
</body>
</html>
"""