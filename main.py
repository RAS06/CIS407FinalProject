import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "library.db"

TABLE_ORDER = ["Author", "Books", "BookCopies", "LibraryMember",
               "Librarian", "BookLoans", "Holds", "Fines"]
ALLOWED_TABLES = set(TABLE_ORDER)

# ==========================================================
#  DATABASE SECTION
# ==========================================================
def createTablesIfNotExists(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Author (
            authorID INTEGER PRIMARY KEY AUTOINCREMENT,
            authorName TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Books (
            bookID INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            authorID INTEGER NOT NULL,
            year_published INTEGER,
            genre TEXT,
            FOREIGN KEY (authorID) REFERENCES Author(authorID)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BookCopies (
            copyID INTEGER PRIMARY KEY AUTOINCREMENT,
            bookID INTEGER NOT NULL,
            FOREIGN KEY (bookID) REFERENCES Books(bookID)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS LibraryMember (
            memberID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            email TEXT,
            DateOfMembership DATE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Librarian (
            librarianID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BookLoans (
            loanID INTEGER PRIMARY KEY AUTOINCREMENT,
            copyID INTEGER NOT NULL,
            memberID INTEGER NOT NULL,
            librarianID INTEGER NOT NULL,
            dateIssued DATE,
            dateDue DATE,
            dateReturned DATE,
            FOREIGN KEY (copyID) REFERENCES BookCopies(copyID)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (memberID) REFERENCES LibraryMember(memberID)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (librarianID) REFERENCES Librarian(librarianID)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Holds (
            holdID INTEGER PRIMARY KEY AUTOINCREMENT,
            memberID INTEGER NOT NULL,
            copyID INTEGER NOT NULL,
            holdDate DATE,
            FOREIGN KEY (memberID) REFERENCES LibraryMember(memberID)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (copyID) REFERENCES BookCopies(copyID)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Fines (
            fineID INTEGER PRIMARY KEY AUTOINCREMENT,
            loanID INTEGER UNIQUE NOT NULL,
            fineAmount REAL NOT NULL,
            fineDate DATE,
            datePaid DATE,
            FOREIGN KEY (loanID) REFERENCES BookLoans(loanID)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        createTablesIfNotExists(cursor)
        conn.commit()

# ---------------------------------------------------------
#  NEW: fine synchroniser
# ---------------------------------------------------------
def sync_fines():
    """
    Ensure every *unreturned* overdue loan has an up-to-date fine row.
    Fine date = loan.dateDue, amount = days-overdue × 0.10
    """
    today = datetime.today().date()
    with get_connection() as conn:
        cursor = conn.cursor()
        # find all unreturned loans that are past due
        cursor.execute("""
            SELECT loanID, dateDue
            FROM BookLoans
            WHERE dateReturned IS NULL
              AND dateDue < ?
        """, (today,))
        overdue = cursor.fetchall()

        for loan_id, due_str in overdue:
            due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
            days_over = (today - due_date).days
            amount = round(days_over * 0.10, 2)

            # insert or replace fine row
            cursor.execute("""
                INSERT INTO Fines (loanID, fineAmount, fineDate, datePaid)
                VALUES (?, ?, ?, NULL)
                ON CONFLICT(loanID) DO UPDATE SET
                    fineAmount=excluded.fineAmount,
                    fineDate=excluded.fineDate,
                    datePaid=NULL
                WHERE datePaid IS NULL
            """, (loan_id, amount, due_str))
        conn.commit()

# ==========================================================
#  HELPER WINDOWS
# ==========================================================
class AddRecordWindow(tk.Toplevel):
    def __init__(self, parent, table_name, columns):
        super().__init__(parent.root)
        self.parent = parent
        self.table_name = table_name
        self.columns = columns
        self.entries = {}

        self.title(f"Add Record — {table_name}")
        self.geometry("400x400")
        self.resizable(False, False)

        tk.Label(self, text=f"Add new record to {table_name}", font=("Arial", 14, "bold")).pack(pady=10)
        form_frame = tk.Frame(self)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for i, col in enumerate(columns):
            tk.Label(form_frame, text=col + ":", anchor="w").grid(row=i, column=0, sticky="w", pady=5)
            entry = tk.Entry(form_frame, width=30)
            # pre-fill dates for BookLoans and Holds and LibraryMember
            if self.table_name == "BookLoans":
                if col == "dateIssued":
                    entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
                elif col == "dateDue":
                    entry.insert(0, (datetime.today() + timedelta(days=14)).strftime("%Y-%m-%d"))
                elif col == "dateReturned":
                    entry.insert(0, "")  # NULL
            elif self.table_name == "Holds" and col == "holdDate":
                entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
            elif self.table_name == "LibraryMember" and col == "DateOfMembership":
                entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
            entry.grid(row=i, column=1, pady=5)
            self.entries[col] = entry

        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Save", command=self.save_record, width=10).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=5)

    def save_record(self):
        data = {col: entry.get() for col, entry in self.entries.items()}
        if not all(v.strip() for v in data.values()):
            messagebox.showwarning("Missing Data", "All fields are required.")
            return

        if self.table_name == "BookLoans":
            if not data.get("dateReturned", "").strip():
                data.pop("dateReturned", None)

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cols = ", ".join(data.keys())
                placeholders = ", ".join(["?" for _ in data])
                cursor.execute(f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholders})", tuple(data.values()))
                conn.commit()
            messagebox.showinfo("Success", f"Record added to {self.table_name}.")
            self.parent.display_table()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add record: {e}")

class EditRecordWindow(tk.Toplevel):
    def __init__(self, parent, table_name, record_data, columns, pk_column):
        super().__init__(parent.root)
        self.parent = parent
        self.table_name = table_name
        self.record_data = record_data
        self.columns = columns
        self.pk_column = pk_column
        self.pk_value = record_data[0]
        self.entries = {}

        self.title(f"Edit Record — {table_name}")
        self.geometry("400x400")
        self.resizable(False, False)

        tk.Label(self, text=f"Edit record in {table_name}", font=("Arial", 14, "bold")).pack(pady=10)
        form_frame = tk.Frame(self)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for i, col in enumerate(columns):
            tk.Label(form_frame, text=col + ":", anchor="w").grid(row=i, column=0, sticky="w", pady=5)
            if col == self.pk_column:
                value_label = tk.Label(form_frame, text=str(self.pk_value), bg="#f0f0f0", relief="sunken")
                value_label.grid(row=i, column=1, pady=5, sticky="ew")
                tk.Label(form_frame, text="(PK)", font=("Arial", 8), fg="gray").grid(row=i, column=2, sticky="w")
            else:
                entry = tk.Entry(form_frame, width=30)
                entry.insert(0, str(record_data[i]))
                entry.grid(row=i, column=1, pady=5)
                self.entries[col] = entry

        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Save", command=self.save_record, width=10).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=5)

    def save_record(self):
        data = {col: entry.get() for col, entry in self.entries.items()}
        if not all(v.strip() for v in data.values()):
            messagebox.showwarning("Missing Data", "All fields are required.")
            return
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                set_clause = ", ".join([f"{col}=?" for col in data])
                cursor.execute(
                    f"UPDATE {self.table_name} SET {set_clause} WHERE {self.pk_column}=?",
                    (*data.values(), self.pk_value)
                )
                conn.commit()
            messagebox.showinfo("Success", "Record updated.")
            self.parent.display_table()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update record: {e}")

class SearchWindow(tk.Toplevel):
    def __init__(self, parent, table_name, columns):
        super().__init__(parent.root)
        self.parent = parent
        self.table_name = table_name
        self.columns = columns
        self.entries = {}

        self.title(f"Search — {table_name}")
        self.geometry("500x400")
        self.resizable(True, True)

        tk.Label(self, text=f"Search {table_name} (leave blank to ignore field)", font=("Arial", 12)).pack(pady=6)
        form_frame = tk.Frame(self)
        form_frame.pack(fill="both", expand=True, padx=15, pady=10)

        for i, col in enumerate(columns):
            tk.Label(form_frame, text=col + ":", anchor="w").grid(row=i, column=0, sticky="w", pady=4)
            entry = tk.Entry(form_frame, width=35)
            entry.grid(row=i, column=1, pady=4, padx=5)
            self.entries[col] = entry

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Search", command=self.do_search, width=12).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=12).pack(side="left", padx=6)

    def do_search(self):
        criteria = {col: ent.get().strip() for col, ent in self.entries.items()}
        if not any(criteria.values()):
            messagebox.showwarning("No Input", "Please fill at least one field to search.")
            return
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                where_parts = []
                args = []
                for col, val in criteria.items():
                    if val:
                        where_parts.append(f"{col} LIKE ?")
                        args.append(f"%{val}%")
                sql = f"SELECT * FROM {self.table_name} WHERE " + " AND ".join(where_parts)
                cursor.execute(sql, args)
                rows = cursor.fetchall()
                headers = [desc[0] for desc in cursor.description]
            if not rows:
                messagebox.showinfo("No Results", "No matching records found.")
                return
            ResultsWindow(self.parent, self.table_name, headers, rows)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Search Error", str(e))

class ResultsWindow(tk.Toplevel):
    def __init__(self, parent, table_name, headers, rows):
        super().__init__(parent.root)
        self.parent = parent
        self.title(f"Search Results — {table_name}")
        self.geometry("700x450")
        self.resizable(True, True)

        tk.Label(self, text=f"Found {len(rows)} record(s)", font=("Arial", 12, "bold")).pack(pady=6)
        tree = ttk.Treeview(self, show="headings")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        scroll = ttk.Scrollbar(self, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")

        tree["columns"] = headers
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, width=120, anchor="center")

        for row in rows:
            tree.insert("", "end", values=row)

        tk.Button(self, text="Close", command=self.destroy, width=10).pack(pady=6)

# ==========================================================
#  MAIN GUI
# ==========================================================
class LibraryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Database Editor")
        self.root.geometry("1000x600")

        tk.Label(root, text="Library Database Editor", font=("Arial", 18, "bold")).pack(pady=10)

        self.table_names = TABLE_ORDER
        toolbar = tk.Frame(root)
        toolbar.pack(fill="x", pady=5)
        self.active_table = tk.StringVar(value="")
        for table in self.table_names:
            tk.Radiobutton(
                toolbar, text=table, variable=self.active_table, value=table,
                indicatoron=False, width=12, command=self.display_table
            ).pack(side="left", padx=2)

        # CRUD + Search + Convert buttons
        crud_frame = tk.Frame(root)
        crud_frame.pack(fill="x", pady=5)
        tk.Button(crud_frame, text="Add Record", command=self.add_record, width=12).pack(side="left", padx=6)
        tk.Button(crud_frame, text="Edit Selected", command=self.edit_record, width=12).pack(side="left", padx=6)
        tk.Button(crud_frame, text="Delete Selected", command=self.delete_record, width=12).pack(side="left", padx=6)
        tk.Button(crud_frame, text="Search", command=self.search_records, width=12).pack(side="left", padx=6)
        tk.Button(crud_frame, text="Refresh", command=self.display_table, width=12).pack(side="left", padx=6)

        # Convert to Loan button (shown only for Holds)
        self.convert_btn = tk.Button(crud_frame, text="Convert to Loan", command=self.convert_hold_to_loan, width=14)
        self.convert_btn.pack(side="left", padx=6)
        self.convert_btn.configure(state="disabled")  # start hidden

        self.tree = ttk.Treeview(root, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        scroll = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")

    # -----------------------------------------------------
    def display_table(self):
        table_name = self.active_table.get()
        if table_name not in ALLOWED_TABLES:
            return
        # toggle Convert button
        if table_name == "Holds":
            self.convert_btn.configure(state="normal")
        else:
            self.convert_btn.configure(state="disabled")

        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree.delete(*self.tree.get_children())
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                self.tree["columns"] = columns
                for col in columns:
                    self.tree.heading(col, text=col)
                    self.tree.column(col, width=120, anchor="center")
                for row in rows:
                    self.tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error loading {table_name}: {e}")

    # -----------------------------------------------------
    def convert_hold_to_loan(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Selection", "Select a hold to convert.")
            return
        hold_values = self.tree.item(selected, "values")
        hold_id = hold_values[0]
        member_id = hold_values[1]
        copy_id = hold_values[2]

        librarian_id = simpledialog.askinteger("Librarian ID", "Enter your librarian ID:")
        if librarian_id is None:
            return  # cancelled

        today_str = datetime.today().strftime("%Y-%m-%d")
        due_str = (datetime.today() + timedelta(days=14)).strftime("%Y-%m-%d")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # insert loan
                cursor.execute("""
                    INSERT INTO BookLoans (copyID, memberID, librarianID, dateIssued, dateDue, dateReturned)
                    VALUES (?, ?, ?, ?, ?, NULL)
                """, (copy_id, member_id, librarian_id, today_str, due_str))
                # remove hold
                cursor.execute("DELETE FROM Holds WHERE holdID=?", (hold_id,))
                conn.commit()
            messagebox.showinfo("Success", "Hold converted to loan.")
            self.display_table()  # refresh Holds
        except Exception as e:
            messagebox.showerror("Error", f"Conversion failed: {e}")

    # -----------------------------------------------------
    def add_record(self):
        table_name = self.active_table.get()
        if table_name not in ALLOWED_TABLES:
            return
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                all_cols = cursor.fetchall()
                editable = [col[1] for col in all_cols
                            if col[5] == 0 and col[1] != "dateReturned"]
            if not editable:
                messagebox.showinfo("No editable fields", f"{table_name} has no user-editable fields.")
                return
            AddRecordWindow(self, table_name, editable)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -----------------------------------------------------
    def edit_record(self):
        table_name = self.active_table.get()
        if table_name not in ALLOWED_TABLES:
            return
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Selection", "Select a record to edit.")
            return
        record = self.tree.item(selected, "values")
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                info = cursor.fetchall()
                columns = [i[1] for i in info]
                pk_col = info[0][1]
            EditRecordWindow(self, table_name, record, columns, pk_col)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -----------------------------------------------------
    def delete_record(self):
        table_name = self.active_table.get()
        if table_name not in ALLOWED_TABLES:
            return
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Selection", "Select a record to delete.")
            return
        record = self.tree.item(selected, "values")
        pk_val = record[0]
        if not messagebox.askyesno("Confirm", f"Delete selected record from {table_name}?"):
            return
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                pk_col = cursor.fetchone()[1]
                cursor.execute(f"DELETE FROM {table_name} WHERE {pk_col}=?", (pk_val,))
                conn.commit()
            messagebox.showinfo("Deleted", "Record removed.")
            self.display_table()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    # -----------------------------------------------------
    def search_records(self):
        table_name = self.active_table.get()
        if table_name not in ALLOWED_TABLES:
            return
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [info[1] for info in cursor.fetchall()]
            SearchWindow(self, table_name, columns)
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ==========================================================
def main():
    init_db()
    sync_fines()   # create / update fine rows on start-up
    root = tk.Tk()
    LibraryApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()