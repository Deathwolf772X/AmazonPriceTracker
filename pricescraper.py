import requests
import bs4
import smtplib
import mysql.connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Your email credentials
EMAIL_ADDRESS = ''
EMAIL_PASSWORD = ''
TO_EMAIL = ''

# MySQL connection setup
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="price_tracker"
)

# Function to send email
def send_email(subject, body, to_email):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())

# Function to get the previous price from the database
def get_previous_price(product_id):
    cursor = db.cursor()
    cursor.execute("SELECT price FROM prices WHERE product_id = %s ORDER BY timestamp DESC LIMIT 1", (product_id,))
    result = cursor.fetchone()
    cursor.fetchall()  # Clear any unread results
    cursor.close()
    return result[0] if result else None

# Function to insert a new price into the database
def insert_price(product_id, product_title, price):
    cursor = db.cursor()
    cursor.execute("INSERT INTO prices (product_id, product_title, price) VALUES (%s, %s, %s)", (product_id, product_title, price))
    db.commit()
    cursor.fetchall()  # Clear any unread results
    cursor.close()

# Function to fetch product IDs from the database
def fetch_product_ids():
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT product_id FROM prices")
    product_ids = cursor.fetchall()
    cursor.close()
    return [row[0] for row in product_ids]

# Function to fetch all tracked products
def fetch_all_products():
    cursor = db.cursor()
    cursor.execute("SELECT product_id, IFNULL(custom_name, product_title) FROM prices GROUP BY product_id, custom_name, product_title")
    products = cursor.fetchall()
    cursor.close()
    return products

# Function to check prices
def check_prices():
    product_list = fetch_product_ids()
    base_url = 'https://www.amazon.co.uk/'
    URL = 'https://www.amazon.co.uk/dp/'

    headers = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    for prod in product_list:
        # Fetch current data for product, including custom name if set
        cursor = db.cursor()
        cursor.execute("SELECT IFNULL(custom_name, product_title) AS display_name FROM prices WHERE product_id = %s", (prod,))
        result = cursor.fetchone()
        cursor.fetchall()  # Clear any unread results
        cursor.close()
        display_name = result[0] if result else "Unknown Product"

        product_url = URL + prod
        product_response = requests.get(product_url, headers=headers)
        soup = bs4.BeautifulSoup(product_response.text, features='lxml')

        # Extracting the product title
        title_tag = soup.find(id="productTitle")
        title = title_tag.get_text().strip() if title_tag else "Title not found"

        # Extracting the whole price part
        whole_price_lines = soup.findAll(class_="a-price-whole")
        whole_price = whole_price_lines[0].get_text().strip().replace('.', '') if whole_price_lines else ""

        # Extracting the fraction price part
        fraction_price_lines = soup.findAll(class_="a-price-fraction")
        fraction_price = fraction_price_lines[0].get_text().strip().replace('.', '') if fraction_price_lines else ""

        # Combining whole price and fraction price with £ symbol
        if whole_price and fraction_price:
            final_price = f"£{whole_price}.{fraction_price}"
        else:
            final_price = "Price not found"

        # Get the previous price from the database
        previous_price = get_previous_price(prod)

        # Check for price change
        if previous_price and final_price != previous_price:
            subject = f"Price change alert for {display_name}"
            body = f"The price of {display_name} has changed from {previous_price} to {final_price}.\nCheck it here: {product_url}"
            send_email(subject, body, TO_EMAIL)

        # Update the product title and price in the database
        cursor = db.cursor()
        cursor.execute("""
            UPDATE prices
            SET product_title = %s, price = %s
            WHERE product_id = %s
        """, (title, final_price, prod))
        db.commit()
        cursor.fetchall()  # Clear any unread results
        cursor.close()

        # Display the results
        print(f"Product ID: {prod}")
        print("Product Title:", display_name)
        print("Price:", final_price)
        print("-" * 40)

def add_product():
    product_id = input("Enter the Amazon product ID to track: ")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM prices WHERE product_id = %s", (product_id,))
    if cursor.fetchone():
        cursor.fetchall()  # Clear any unread results
        print(f"Product {product_id} is already being tracked.")
    else:
        # Insert the product ID into the database
        cursor.execute("INSERT INTO prices (product_id) VALUES (%s)", (product_id,))
        db.commit()
        print(f"Product {product_id} added for tracking.")

        # Fetch the product details from Amazon immediately
        base_url = 'https://www.amazon.co.uk/'
        URL = 'https://www.amazon.co.uk/dp/'
        headers = {
            "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        }

        product_url = URL + product_id
        product_response = requests.get(product_url, headers=headers)
        soup = bs4.BeautifulSoup(product_response.text, features='lxml')

        # Extracting the product title
        title_tag = soup.find(id="productTitle")
        title = title_tag.get_text().strip() if title_tag else "Title not found"

        # Extracting the whole price part
        whole_price_lines = soup.findAll(class_="a-price-whole")
        whole_price = whole_price_lines[0].get_text().strip().replace('.', '') if whole_price_lines else ""

        # Extracting the fraction price part
        fraction_price_lines = soup.findAll(class_="a-price-fraction")
        fraction_price = fraction_price_lines[0].get_text().strip().replace('.', '') if fraction_price_lines else ""

        # Combining whole price and fraction price with £ symbol
        if whole_price and fraction_price:
            final_price = f"£{whole_price}.{fraction_price}"
        else:
            final_price = "Price not found"

        # Update the product title and initial price in the database
        cursor.execute("""
            UPDATE prices
            SET product_title = %s, price = %s
            WHERE product_id = %s
        """, (title, final_price, product_id))
        db.commit()
        cursor.close()

        print(f"Product {product_id} titled '{title}' with initial price {final_price} added.")

# Function to remove a product
def remove_product():
    product_id = input("Enter the Amazon product ID to stop tracking: ")
    cursor = db.cursor()
    cursor.execute("DELETE FROM prices WHERE product_id = %s", (product_id,))
    db.commit()
    cursor.fetchall()  # Clear any unread results
    cursor.close()
    print(f"Product {product_id} removed from tracking.")

# Function to view price history
def view_price_history():
    product_id = input("Enter the Amazon product ID to view price history: ")
    cursor = db.cursor()
    cursor.execute("SELECT product_title, price, timestamp FROM prices WHERE product_id = %s ORDER BY timestamp ASC", (product_id,))
    rows = cursor.fetchall()
    cursor.close()
    for row in rows:
        print(f"Title: {row[0]}, Price: {row[1]}, Timestamp: {row[2]}")

# Function to view current tracked products
def view_tracked_products():
    products = fetch_all_products()
    if products:
        print("Currently tracked products:")
        for product in products:
            print(f"Product ID: {product[0]}, Product Title: {product[1]}")
    else:
        print("No products are currently being tracked.")

# Function to set a custom name for a product
def set_custom_name():
    product_id = input("Enter the Amazon product ID for which you want to set a custom name: ")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM prices WHERE product_id = %s", (product_id,))
    result = cursor.fetchall()
    if result:
        custom_name = input("Enter the custom name: ")
        cursor.execute("UPDATE prices SET custom_name = %s WHERE product_id = %s", (custom_name, product_id))
        db.commit()
        cursor.fetchall()  # Clear any unread results
        print(f"Custom name '{custom_name}' set for product {product_id}.")
    else:
        print(f"Product {product_id} is not being tracked.")
    cursor.close()

# Main menu
def main():
    while True:
        print("1. Check prices")
        print("2. Add a product")
        print("3. Remove a product")
        print("4. View price history")
        print("5. View current tracked products")
        print("6. Set custom name for a product")
        print("7. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            check_prices()
        elif choice == '2':
            add_product()
        elif choice == '3':
            remove_product()
        elif choice == '4':
            view_price_history()
        elif choice == '5':
            view_tracked_products()
        elif choice == '6':
            set_custom_name()
        elif choice == '7':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
