import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
import os

class FinanceTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Personal Finance Tracker")
        self.root.geometry("750x400")  # Adjust this as necessary
        
        # Constants
        self.INCOME_CATEGORIES = ['Salary', 'Investment', 'Other']
        self.EXPENSE_CATEGORIES = ['Food', 'Utilities', 'Rent', 'Entertainment', 'Healthcare', 'Transportation']
        
        # Database initialization
        self.init_database()
        
        # Create main container
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create and setup UI components
        self.setup_ui()
        
        # Initial data load
        self.refresh_transaction_view()

    def init_database(self):
        """Initialize database connection and create tables"""
        try:
            self.conn = sqlite3.connect('finance_tracker.db')
            self.cursor = self.conn.cursor()
            
            # Create transactions table with additional fields
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                type TEXT CHECK(type IN ('income', 'expense')),
                amount DECIMAL(10,2) CHECK(amount > 0),
                category TEXT,
                description TEXT,
                date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            self.conn.commit()
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")
            raise
    def update_categories(self, event=None):
        """Update category options based on transaction type"""
        transaction_type = self.transaction_type.get()
        if transaction_type == 'income':
            self.category_combo['values'] = self.INCOME_CATEGORIES
        elif transaction_type == 'expense':
            self.category_combo['values'] = self.EXPENSE_CATEGORIES
        self.category_combo.set('')  # Reset the category combobox
    
    def clear_all_transactions(self):
        """Clear all transactions and reset financial data"""
        try:
            # Confirm action
            confirm = messagebox.askyesno("Clear All", "Are you sure you want to delete all transactions?")
            if confirm:
                # Delete all transactions from the database
                self.cursor.execute("DELETE FROM transactions")
                self.conn.commit()
                
                # Refresh the transaction view and dashboard
                self.refresh_transaction_view()
                self.update_dashboard()

                messagebox.showinfo("Success", "All transactions have been cleared.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to clear transactions: {str(e)}")


    def setup_add_transaction_form(self):
        """Set up the form for adding new transactions"""
        # Transaction type
        ttk.Label(self.add_transaction_frame, text="Type:").grid(row=0, column=0, padx=5, pady=5)
        self.transaction_type = ttk.Combobox(self.add_transaction_frame, values=['income', 'expense'])
        self.transaction_type.grid(row=0, column=1, padx=5, pady=5)
        self.transaction_type.bind('<<ComboboxSelected>>', self.update_categories)
        
        # Amount
        ttk.Label(self.add_transaction_frame, text="Amount:").grid(row=1, column=0, padx=5, pady=5)
        self.amount_entry = ttk.Entry(self.add_transaction_frame)
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Category
        ttk.Label(self.add_transaction_frame, text="Category:").grid(row=2, column=0, padx=5, pady=5)
        self.category_combo = ttk.Combobox(self.add_transaction_frame)
        self.category_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Description
        ttk.Label(self.add_transaction_frame, text="Description:").grid(row=3, column=0, padx=5, pady=5)
        self.description_entry = ttk.Entry(self.add_transaction_frame)
        self.description_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Date
        ttk.Label(self.add_transaction_frame, text="Date (YYYY-MM-DD):").grid(row=4, column=0, padx=5, pady=5)
        self.date_entry = ttk.Entry(self.add_transaction_frame)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=4, column=1, padx=5, pady=5)
        
        # Submit button
        ttk.Button(self.add_transaction_frame, text="Add Transaction", 
                command=self.add_transaction).grid(row=5, column=0, columnspan=2, pady=20)

    def setup_dashboard(self):
        """Set up the dashboard with summary and charts"""
        # Summary section
        summary_frame = ttk.LabelFrame(self.dashboard_frame, text="Financial Summary", padding="10")
        summary_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.summary_labels = {
            'income': ttk.Label(summary_frame, text="Total Income: $0.00"),
            'expense': ttk.Label(summary_frame, text="Total Expenses: $0.00"),
            'balance': ttk.Label(summary_frame, text="Net Balance: $0.00")
        }
        
        for idx, label in enumerate(self.summary_labels.values()):
            label.grid(row=idx, column=0, sticky=tk.W, pady=2)
        
        self.update_dashboard()

    def setup_transactions_view(self):
        """Set up the transactions view with filtering and table"""
        # Filters frame
        filters_frame = ttk.LabelFrame(self.transactions_frame, text="Filters", padding="10")
        filters_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(filters_frame, text="Date Range:").grid(row=0, column=0, padx=5)
        self.start_date = ttk.Entry(filters_frame, width=10)
        self.start_date.grid(row=0, column=1, padx=5)
        ttk.Label(filters_frame, text="to").grid(row=0, column=2, padx=5)
        self.end_date = ttk.Entry(filters_frame, width=10)
        self.end_date.grid(row=0, column=3, padx=5)
        
        ttk.Button(filters_frame, text="Apply Filters", command=self.apply_filters).grid(row=0, column=4, padx=5)
        ttk.Button(filters_frame, text="Reset Filters", command=self.reset_filters).grid(row=0, column=5, padx=5)
        
        # Transactions table
        columns = ('id', 'type', 'amount', 'category', 'description', 'date')
        self.tree = ttk.Treeview(self.transactions_frame, columns=columns, show='headings')
        
        # Define column headings
        for col in columns:
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=100)
        
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.transactions_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Context menu
        self.create_context_menu()

    def create_context_menu(self):
        """Create a right-click context menu for transaction row options"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Delete", command=self.delete_transaction)
        self.context_menu.add_command(label="Edit", command=self.edit_transaction)
        
        def show_context_menu(event):
            """Display the context menu"""
            selected_item = self.tree.selection()
            if selected_item:
                self.context_menu.post(event.x_root, event.y_root)
        
        self.tree.bind("<Button-3>", show_context_menu)

    def delete_transaction(self):
        """Delete a selected transaction"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "No transaction selected for deletion.")
            return
        
        transaction_id = self.tree.item(selected_item)['values'][0]
        try:
            self.cursor.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            self.conn.commit()
            self.refresh_transaction_view()
            self.update_dashboard()
            messagebox.showinfo("Success", "Transaction deleted successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Failed to delete transaction: {str(e)}")

    def edit_transaction(self):
        """Edit a selected transaction"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "No transaction selected for editing.")
            return
        
        transaction_id = self.tree.item(selected_item)['values'][0]
        self.cursor.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
        transaction = self.cursor.fetchone()
        
        # Populating fields for editing (could use a separate popup form here)
        self.transaction_type.set(transaction[1])
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, transaction[2])
        self.category_combo.set(transaction[3])
        self.description_entry.delete(0, tk.END)
        self.description_entry.insert(0, transaction[4])
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, transaction[5])
        
        # You can now add a save button to save updates to the transaction

    def apply_filters(self):
        """Apply date range filters"""
        start_date = self.start_date.get()
        end_date = self.end_date.get()
        
        valid_start, start_error = self.validate_date(start_date)
        valid_end, end_error = self.validate_date(end_date)
        
        if not valid_start or not valid_end:
            messagebox.showerror("Invalid Date", "Please enter valid start and end dates (YYYY-MM-DD).")
            return
        
        try:
            self.cursor.execute("""
            SELECT id, type, amount, category, description, date
            FROM transactions
            WHERE date BETWEEN ? AND ?
            """, (start_date, end_date))
            rows = self.cursor.fetchall()
            self.populate_transaction_table(rows)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to apply filter: {str(e)}")

    def reset_filters(self):
        """Reset filters and reload all transactions"""
        self.start_date.delete(0, tk.END)
        self.end_date.delete(0, tk.END)
        self.refresh_transaction_view()

    def validate_date(self, date_str):
        """Check if a date is valid"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True, ""
        except ValueError:
            return False, "Invalid date format"

    def refresh_transaction_view(self):
        """Refresh the transaction list view"""
        try:
            # Query to select all transactions
            self.cursor.execute("SELECT id, type, amount, category, description, date FROM transactions")
            rows = self.cursor.fetchall()
            
            # Clear the treeview before repopulating
            self.populate_transaction_table(rows)
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Failed to refresh transactions: {str(e)}")


    def populate_transaction_table(self, rows):
        """Populate the transaction table with rows"""
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in rows:
            self.tree.insert('', 'end', values=row)

    def update_dashboard(self):
        """Update the financial summary and charts"""
        try:
            # Fetch the total income
            self.cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
            income_total = self.cursor.fetchone()[0] or 0
            
            # Update income summary
            self.summary_labels['income'].config(text=f"Total Income: ${income_total:,.2f}")
            
            # Fetch the total expenses
            self.cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
            expense_total = self.cursor.fetchone()[0] or 0
            
            # Update expense summary
            self.summary_labels['expense'].config(text=f"Total Expenses: ${expense_total:,.2f}")
            
            # Calculate the balance
            balance = income_total - expense_total
            self.summary_labels['balance'].config(text=f"Net Balance: ${balance:,.2f}")

        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Failed to update dashboard: {str(e)}")

    
    def add_transaction(self):
        """Add a new transaction to the database"""
        transaction_type = self.transaction_type.get()
        amount = self.amount_entry.get()
        category = self.category_combo.get()
        description = self.description_entry.get()
        date = self.date_entry.get()

        try:
            # Validate and insert transaction into database
            if transaction_type and amount and category and description and date:
                # Convert amount to float before inserting into the database
                self.cursor.execute("""
                INSERT INTO transactions (type, amount, category, description, date)
                VALUES (?, ?, ?, ?, ?)
                """, (transaction_type, float(amount), category, description, date))
                self.conn.commit()
                messagebox.showinfo("Success", "Transaction added successfully.")
                self.refresh_transaction_view()
                self.update_dashboard()
                self.clear_add_transaction_form()
            else:
                messagebox.showerror("Input Error", "All fields must be filled.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Amount should be a valid number.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add transaction: {str(e)}")
    def setup_ui(self):
        """Set up the main UI components"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add space between the components in the main container
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Dashboard tab
        self.dashboard_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        
        # Clear All Transactions Button (Make sure this is in the correct UI setup)
        ttk.Button(self.dashboard_frame, text="Clear All Transactions", 
                command=self.clear_all_transactions).grid(row=1, column=0, pady=20)
        
        # Setup Dashboard components
        self.setup_dashboard()
        
        # Transactions tab
        self.transactions_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.transactions_frame, text="Transactions")
        self.setup_transactions_view()
        
        # Add Transaction tab
        self.add_transaction_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.add_transaction_frame, text="Add Transaction")
        self.setup_add_transaction_form()


    def clear_add_transaction_form(self):
        """Clear the add transaction form"""
        self.transaction_type.set('')
        self.amount_entry.delete(0, tk.END)
        self.category_combo.set('')
        self.description_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)

def main():
    # Create the root Tkinter window
    root = tk.Tk()
    
    # Create an instance of the FinanceTrackerGUI class
    app = FinanceTrackerGUI(root)
    
    # Start the Tkinter event loop
    root.mainloop()

if __name__ == "__main__":
    main()
