import csv
import os
from datetime import datetime

# CSV file name
CSV_FILE = "expenses.csv"

def initialize_csv():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Date', 'Category', 'Description', 'Amount'])
        print(f"✓ {CSV_FILE} file created successfully!\n")

def add_expenses():
    """Add multiple expenses until user says no"""
    expenses = []
    
    print("\n" + "="*50)
    print(" ___ADD EXPENSES___")
    print("="*50)
    
    while True:
        print("\n--- Enter Expense Details ---")
        
        # Get expense details
        category = input("Category (e.g., Food, Transport, Shopping): ").strip()
        description = input("Description: ").strip()
        
        # Get amount with validation
        while True:
            try:
                amount = float(input("Amount (₹): ").strip())
                if amount <= 0:
                    print("⚠ Amount must be greater than 0. Please try again.")
                    continue
                break
            except ValueError:
                print("⚠ Invalid amount! Please enter a number.")
        
        # Get current date and time
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store expense
        expenses.append([date, category, description, amount])
        print(f"✓ Expense of ₹{amount} added successfully!")
        
        # Ask if user wants to add more
        while True:
            more = input("\nDo you want to add more expenses? (yes/no): ").strip().lower()
            if more in ['yes', 'y', 'no', 'n']:
                break
            print("⚠ Please enter 'yes' or 'no'")
        
        if more in ['no', 'n']:
            break
    
    # Save all expenses to CSV
    if expenses:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(expenses)
        
        print(f"\n✓ Total {len(expenses)} expense(s) saved to {CSV_FILE}")
    
    input("\nPress Enter to continue...")

def view_history():
    """View all expense history from CSV"""
    print("\n" + "="*50)
    print("           EXPENSE HISTORY")
    print("="*50)
    
    if not os.path.exists(CSV_FILE):
        print("\n⚠ No expense history found! CSV file doesn't exist.")
        input("\nPress Enter to continue...")
        return
    
    with open(CSV_FILE, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)
        
        if len(rows) <= 1:  # Only header or empty
            print("\n⚠ No expenses recorded yet!")
        else:
            print("\n{:<20} {:<15} {:<25} {:<10}".format("Date", "Category", "Description", "Amount (₹)"))
            print("-" * 70)
            
            for row in rows[1:]:  # Skip header
                if len(row) == 4:
                    print("{:<20} {:<15} {:<25} {:<10}".format(row[0], row[1], row[2], row[3]))
    
    input("\nPress Enter to continue...")

def view_total():
    """Calculate and display total of all transactions"""
    print("\n" + "="*50)
    print("        TOTAL TRANSACTIONS")
    print("="*50)
    
    if not os.path.exists(CSV_FILE):
        print("\n⚠ No expense history found! CSV file doesn't exist.")
        input("\nPress Enter to continue...")
        return
    
    total = 0
    count = 0
    
    with open(CSV_FILE, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        
        for row in reader:
            if len(row) == 4:
                try:
                    amount = float(row[3])
                    total += amount
                    count += 1
                except ValueError:
                    continue
    
    if count == 0:
        print("\n⚠ No expenses recorded yet!")
    else:
        print(f"\n📊 Total Number of Transactions: {count}")
        print(f"💰 Total Amount Spent: ₹{total:.2f}")
    
    input("\nPress Enter to continue...")

def display_menu():
    """Display main menu"""
    print("\n" + "="*50)
    print("        EXPENSE TRACKER")
    print("="*50)
    print("\n1. Add Expenses")
    print("2. View Expense History")
    print("3. Check Total Transactions")
    print("4. Exit")
    print("\n" + "="*50)

def main():
    """Main function to run the expense tracker"""
    # Initialize CSV file
    initialize_csv()
    
    while True:
        display_menu()
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            add_expenses()
        elif choice == '2':
            view_history()
        elif choice == '3':
            view_total()
        elif choice == '4':
            print("\n👋 Thank you for using Expense Tracker! Goodbye!")
            break
        else:
            print("\n⚠ Invalid choice! Please enter a number between 1-4.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
