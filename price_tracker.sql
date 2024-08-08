CREATE DATABASE price_tracker;

USE price_tracker;

CREATE TABLE prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(20),
    product_title VARCHAR(255),
    custom_name VARCHAR(255), -- Column to store custom product names
    price VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

SHOW DATABASES;
SHOW TABLES;
