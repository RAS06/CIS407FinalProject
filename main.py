import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3

DB_FILE = "library.db"


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
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BookCopies (
            copyID INTEGER PRIMARY KEY AUTOINCREMENT,
            bookID INTEGER NOT NULL,
            FOREIGN KEY (bookID) REFERENCES Books(bookID)
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
            FOREIGN KEY (copyID) REFERENCES BookCopies(copyID),
            FOREIGN KEY (memberID) REFERENCES LibraryMember(memberID),
            FOREIGN KEY (librarianID) REFERENCES Librarian(librarianID)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Holds (
            holdID INTEGER PRIMARY KEY AUTOINCREMENT,
            memberID INTEGER NOT NULL,
            bookID INTEGER NOT NULL,
            holdDate DATE,
            FOREIGN KEY (memberID) REFERENCES LibraryMember(memberID),
            FOREIGN KEY (bookID) REFERENCES Books(bookID)
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
        );
    """)


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    createTablesIfNotExists(cursor)
    conn.commit()
    conn.close()


#HELPER CLASS
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
            conn = get_connection()
            cursor = conn.cursor()
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            cursor.execute(f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholders})", tuple(data.values()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Record added to {self.table_name}.")
            self.parent.display_table()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add record: {e}")


# ==========================================================
#  GUI SECTION
# ==========================================================
class LibraryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Database Editor")
        self.root.geometry("1000x600")

        title_label = tk.Label(root, text="Library Database Editor", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)

        # --- Top toolbar: table selector ---
        self.table_names = [
            "Author",
            "Books",
            "BookCopies",
            "LibraryMember",
            "Librarian",
            "BookLoans",
            "Holds",
            "Fines",
        ]
        toolbar = tk.Frame(root)
        toolbar.pack(fill="x", pady=5)

        self.active_table = tk.StringVar(value="")
        for table in self.table_names:
            tk.Radiobutton(
                toolbar,
                text=table,
                variable=self.active_table,
                value=table,
                indicatoron=False,
                width=12,
                command=self.display_table
            ).pack(side="left", padx=2)

        # --- Middle toolbar: CRUD operations ---
        crud_frame = tk.Frame(root)
        crud_frame.pack(fill="x", pady=5)

        tk.Button(crud_frame, text="Add Record", command=self.add_record).pack(side="left", padx=10)
        tk.Button(crud_frame, text="Edit Selected", command=self.edit_record).pack(side="left", padx=10)
        tk.Button(crud_frame, text="Delete Selected", command=self.delete_record).pack(side="left", padx=10)
        tk.Button(crud_frame, text="Refresh", command=self.display_table).pack(side="left", padx=10)

        # --- Table display ---
        self.tree = ttk.Treeview(root, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    # --- Helper: refresh table display ---
    def display_table(self):
        table_name = self.active_table.get()
        if not table_name:
            return

        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree.delete(*self.tree.get_children())

        try:
            conn = get_connection()
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

        finally:
            conn.close()

    # --- CRUD Operations ---
    def add_record(self):
        table_name = self.active_table.get()
        if not table_name:
            messagebox.showwarning("No Table Selected", "Please select a table first.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            all_columns = cursor.fetchall()
            conn.close()

            # Exclude PK columns (autoincrement or PRIMARY KEY)
            editable_columns = [col[1] for col in all_columns if col[5] == 0]

            if not editable_columns:
                messagebox.showinfo("No Editable Fields", f"{table_name} has no user-editable fields.")
                return

            AddRecordWindow(self, table_name, editable_columns)

        except Exception as e:
            messagebox.showerror("Error", f"Could not open add record window: {e}")

    def edit_record(self):
        table_name = self.active_table.get()
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Selection", "Select a record to edit.")
            return

        record = self.tree.item(selected, "values")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        conn.close()

        pk_column = columns[0]
        pk_value = record[0]
        editable_columns = columns[1:]  # skip PK

        new_values = {}
        for i, col in enumerate(editable_columns, start=1):
            value = simpledialog.askstring("Edit", f"{col} (current: {record[i]}):")
            if value is not None:
                new_values[col] = value

        if not new_values:
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            set_clause = ", ".join([f"{col}=?" for col in new_values])
            cursor.execute(
                f"UPDATE {table_name} SET {set_clause} WHERE {pk_column}=?",
                (*new_values.values(), pk_value)
            )
            conn.commit()
            messagebox.showinfo("Success", "Record updated.")
            self.display_table()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update record: {e}")
        finally:
            conn.close()

    def delete_record(self):
        table_name = self.active_table.get()
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Selection", "Select a record to delete.")
            return

        record = self.tree.item(selected, "values")
        pk_value = record[0]

        if not messagebox.askyesno("Confirm", f"Delete selected record from {table_name}?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            pk_column = cursor.fetchone()[1]
            cursor.execute(f"DELETE FROM {table_name} WHERE {pk_column}=?", (pk_value,))
            conn.commit()
            messagebox.showinfo("Deleted", f"Record removed from {table_name}.")
            self.display_table()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete record: {e}")
        finally:
            conn.close()



# ==========================================================
#  MAIN PROGRAM ENTRY
# ==========================================================
def main():
    init_db()
    root = tk.Tk()
    app = LibraryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
