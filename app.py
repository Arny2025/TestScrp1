from flask import Flask, render_template_string, request, send_from_directory
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

# Neon UI Template
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Price Drop Properties</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 2rem;
            background-color: #0E1117;
            font-family: 'Space Grotesk', sans-serif;
            color: #E2E8F0;
        }
        h2 {
            font-size: 32px;
            font-weight: 700;
            color: #00FFFF;
            text-shadow: 0 0 8px rgba(0, 255, 255, 0.6);
            margin-bottom: 1rem;
        }
        form {
            margin-bottom: 2rem;
        }
        select, input[type="submit"] {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            padding: 0.6rem 1rem;
            color: #fff;
            border-radius: 10px;
            margin-right: 1rem;
            font-size: 16px;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 10px #00FFFF44;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            overflow: hidden;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 30px rgba(0, 255, 255, 0.05);
        }
        th, td {
            padding: 1rem;
            text-align: left;
        }
        th {
            background: rgba(255, 255, 255, 0.1);
            color: #00FFFF;
            text-shadow: 0 0 6px rgba(0, 255, 255, 0.3);
            font-size: 16px;
        }
        td {
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            color: #E2E8F0;
        }
        tr:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        a {
            color: #9F7AEA;
            text-decoration: none;
            font-weight: bold;
        }
        a:hover {
            text-shadow: 0 0 5px #9F7AEA;
        }
    </style>
</head>
<body>
    <h2>Properties Listed Below Last Sale Price</h2>
    <form method="get">
        <label for="suburb">Suburb:</label>
        <select name="suburb">
            <option value="">All</option>
            {% for s in suburbs %}
                <option value="{{ s }}" {% if s == suburb %}selected{% endif %}>{{ s.title() }}</option>
            {% endfor %}
        </select>
        <input type="submit" value="Filter">
    </form>
    <table>
        <tr>
            <th>Address</th>
            <th>Current Price</th>
            <th>Last Sold</th>
            <th>Link</th>
        </tr>
        {% for p in properties %}
        <tr>
            <td>{{ p.address }}</td>
            <td>{{ p.price }}</td>
            <td>{{ p.last_price }}</td>
            <td><a href="{{ p.link }}" target="_blank">View</a></td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

# List of target suburbs
bayside_suburbs = [
    "brighton", "hampton", "sandringham", "black rock", "beaumaris", "cheltenham",
    "mentone", "aspendale", "chelsea", "edithvale", "bonbeach", "seaford", "carrum","point cook"
]

# Real scraping using Playwright
def extract_properties(suburb):
    results = []
    suburb_query = suburb.lower().replace(" ", "-")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, 9):
            url = f"https://www.realestate.com.au/buy/in-{suburb_query}+vic/list-{page_num}"
            try:
                page.goto(url, timeout=90000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Save for debugging
                with open(f"debug_{suburb_query}_page{page_num}.html", "w", encoding="utf-8") as f:
                    f.write(soup.prettify())

                listings = soup.select('[data-testid="listing-card-wrapper"]')
                for listing in listings:
                    try:
                        address = listing.select_one('[data-testid="address-label"]').text.strip()
                        price = listing.select_one('[data-testid="listing-price"]').text.strip()
                        link = "https://www.realestate.com.au" + listing.find("a")["href"]

                        # Placeholder last price logic
                        last_price = "$11,100,000"  # Replace with real sale scraping later

                        # Add only if lower than fake last price
                        if "$" in price and price.replace("$", "").replace(",", "").isdigit():
                            current_price_val = int(price.replace("$", "").replace(",", ""))
                            last_price_val = int(last_price.replace("$", "").replace(",", ""))
                            if current_price_val < last_price_val:
                                results.append({
                                    "address": address,
                                    "price": price,
                                    "last_price": last_price,
                                    "link": link
                                })
                    except Exception:
                        continue

            except Exception as e:
                print(f"Error loading {url}: {e}")
                continue

        browser.close()
    return results

# Home route
@app.route("/")
def home():
    suburb = request.args.get("suburb", "").lower()
    if suburb:
        properties = extract_properties(suburb)
    else:
        properties = []
        for s in bayside_suburbs:
            properties.extend(extract_properties(s))
    return render_template_string(TEMPLATE, properties=properties, suburbs=bayside_suburbs, suburb=suburb)

# Route to serve debug HTML
@app.route("/debug/<filename>")
def serve_debug_file(filename):
    return send_from_directory(".", filename)

# App runner for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
