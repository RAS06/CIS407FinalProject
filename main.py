import sqlite3
from sqlite3 import Cursor


def createTablesIfNotExists(cursor: Cursor):
    # Create Author table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Author (
            authorID INTEGER PRIMARY KEY AUTOINCREMENT,
            authorName TEXT NOT NULL
        );
    """)

    # Create Books table
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

    # Create BookCopies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BookCopies (
            copyID INTEGER PRIMARY KEY AUTOINCREMENT,
            bookID INTEGER NOT NULL,
            FOREIGN KEY (bookID) REFERENCES Books(bookID)
        );
    """)

    # Create LibraryMember table
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

    # Create Librarian table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Librarian (
            librarianID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT
        );
    """)

    # Create BookLoans table
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

    # Create Holds table
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

    # Create Fines table (one-to-one with BookLoans)
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


def main():
    # Connect to SQLite database
    conn = sqlite3.connect("library.db")
    conn.execute("PRAGMA foreign_keys = ON;")

    cursor = conn.cursor()
    createTablesIfNotExists(cursor)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
