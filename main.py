from datetime import datetime 
import matplotlib.pyplot as plt



def read_sales_data(file_path):
    '''
    basic function that reads data from csv file with delimiter = ','
    '''
    sales = []
    with open(file_path, 'r', encoding='utf-8') as file:
        # Read the header line
        header = file.readline().strip().split(',')
        sales = []
        # Read the remaining lines
        for line in file:
            # Split each line by comma and strip whitespace
            row = line.strip().split(',')
            cur_row_dict = dict()
            for i in range(len(row)):
                if len(row) == 4:
                    name = row[0].strip()  # Product name
                    cur_row_dict['product_name'] = name
                    quantity = int(row[1].strip())  # Quantity
                    cur_row_dict['quantity'] = quantity
                    price = float(row[2].strip())  # Price
                    cur_row_dict['price'] = price
                    dt = datetime.strptime(row[3].strip(), '%Y-%m-%d')  # Date
                    cur_row_dict['dt'] = dt
                    
                    
            sales.append(cur_row_dict)

    return sales




def total_sales_per_product(sales_data):
    '''
    calculate total quantity sold for each product name
    '''
    total_sales_by_product_name = dict()
    for item in sales_data:
        if item['product_name'] not in total_sales_by_product_name:
            total_sales_by_product_name[item['product_name']] = item['quantity']
        else:
            total_sales_by_product_name[item['product_name']] += item['quantity']
   
    return total_sales_by_product_name




def sales_over_time(sales_data):
    '''
    calculate total quantity sold for each date
    '''
    sales_by_date = dict()

    for item in sales_data:
        cur_date = item['dt']
        cur_date = cur_date.strftime('%d %B %Y')
        if cur_date not in sales_by_date:
            sales_by_date[cur_date] = item['quantity']
        else:
            sales_by_date[cur_date] += item['quantity']

    return sales_by_date

def max_profit_product(sales_data):
    '''
    show most profitable product and its total profit
    '''
    temp = total_sales_per_product(sales_data)#this is dict of name:total_quantity
    total_profit_by_product =  dict()

    for item in sales_data:
        price = item['price']
        name = item['product_name']
        quantity = temp[name]        
        total = price*quantity
        if name not in total_profit_by_product:
            total_profit_by_product[name] = total
    

    total_profit_by_product = [[k,v] for k,v in total_profit_by_product.items()]
    total_profit_by_product.sort(key = lambda x: -x[1])
    most_profitable_product, total_profit = total_profit_by_product[0]
    return most_profitable_product, total_profit

 
def max_sales_day(sales_data):
    '''
    calculate the day when max quantity is sold
    '''
    sales_by_date = sales_over_time(sales_data)
    max_sales_date = max(sales_by_date, key=sales_by_date.get)
    max_sales_amount = sales_by_date[max_sales_date]
    return max_sales_date, max_sales_amount



if __name__ == "__main__":
    #read and populate the sales_data
    sales_data = read_sales_data('sales_data.csv')

    # Total sales per product
    total_sales = total_sales_per_product(sales_data)
    print("Total sales per product:", total_sales)
    
    # Determine the product with the highest revenue
    best_product = max(total_sales, key=total_sales.get)
    print("Product with the highest revenue:", best_product)
    
    # Sales over time
    sales_by_date = sales_over_time(sales_data)
    print("Sales by date:", sales_by_date)
    
    # Determine the day with the highest sales
    best_day = max(sales_by_date, key=sales_by_date.get)
    print("Day with the highest sales:", best_day)
    
    # Plotting
    # 1. Total sales per product
    plt.figure(figsize=(10, 5))
    plt.bar(total_sales.keys(), total_sales.values(), color='blue')
    plt.title('Total Sales per Product')
    plt.xlabel('Product')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    
    # 2. Total sales over time
    plt.figure(figsize=(10, 5))
    plt.plot(sales_by_date.keys(), sales_by_date.values(), marker='o', color='green')
    plt.title('Total Sales Over Time')
    plt.xlabel('Date')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    