import tkinter as tk
import sqlite3
from sqlite3 import Cursor



def createTablesIfNotExists(cursor: Cursor):
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Authors
                   (
                       authorID
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       authorName
                       TEXT
                       NOT
                       NULL
                   );
                   """)

    # Create Books table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Books
                   (
                       bookID
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       title
                       TEXT
                       NOT
                       NULL,
                       authorID
                       INTEGER
                       NOT
                       NULL,
                       year_published
                       INTEGER,
                       genre
                       VARCHAR
                   (
                       50
                   ),
                       FOREIGN KEY
                   (
                       authorID
                   ) REFERENCES Authors
                   (
                       authorID
                   )
                       );
                   """)

    # Create BookCopies table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS BookCopies
                   (
                       copyID
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       bookID
                       INTEGER
                       NOT
                       NULL,
                       FOREIGN
                       KEY
                   (
                       bookID
                   ) REFERENCES Books
                   (
                       bookID
                   )
                       );
                   """)

    # Create LibraryMembers table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS LibraryMembers
                   (
                       memberID
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       name
                       VARCHAR
                   (
                       50
                   ) NOT NULL,
                       address TEXT,
                       phone TEXT,
                       email TEXT,
                       DateOfMembership DATE
                       );
                   """)

    # Create Librarians table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Librarians
                   (
                       librarianID
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       name
                       VARCHAR
                   (
                       50
                   ) NOT NULL,
                       email TEXT,
                       phone TEXT
                       );
                   """)

    # Create BookLoans table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS BookLoans
                   (
                       loanID
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       copyID
                       INTEGER
                       NOT
                       NULL,
                       memberID
                       INTEGER
                       NOT
                       NULL,
                       librarianID
                       INTEGER
                       NOT
                       NULL,
                       dateIssued
                       DATE,
                       dateDue
                       DATE,
                       dateReturned
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       copyID
                   ) REFERENCES BookCopies
                   (
                       copyID
                   ),
                       FOREIGN KEY
                   (
                       memberID
                   ) REFERENCES LibraryMembers
                   (
                       memberID
                   ),
                       FOREIGN KEY
                   (
                       librarianID
                   ) REFERENCES Librarians
                   (
                       librarianID
                   )
                       );
                   """)

def main():


# Connect to SQLite database (creates file if it doesn't exist)
    conn = sqlite3.connect("library.db")

    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON;")

    # Create cursor
    cursor = conn.cursor()

    # Create Authors table
    createTablesIfNotExists(cursor)

# Commit and close connection
    conn.commit()
    conn.close()

main()