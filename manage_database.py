"""
Auto Get Tunes - Database Management Utility

This utility provides a command-line interface for managing the tunes database.
It allows users to view, search, and update database entries, particularly
for adding project information to downloaded songs.

Key Features:
- Display all database entries with status information
- Update project information for specific entries
- Search entries by project name
- Show database statistics
- Interactive menu-driven interface

Author: Claude Sonnet 3.5 (Anthropic) under supervision of Guillaume Blain
"""

import json
import os

# Path to the database (in the code subfolder relative to this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(SCRIPT_DIR, "code", 'tunes_database.json')

def load_database():
    """
    Load the existing database from JSON file.
    
    Returns:
        list: Database entries or empty list if file doesn't exist
    """
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_database(data):
    """
    Save the database to JSON file.
    
    Args:
        data (list): Database entries to save
    """
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def display_database():
    """
    Display all entries in the database with status information.
    Shows title, download status, project, download path, and URL for each entry.
    """
    database = load_database()
    if not database:
        print("The database is empty.")
        return
    
    print(f"\n=== TUNES DATABASE ({len(database)} entries) ===")
    print("-" * 80)
    
    for idx, entry in enumerate(database, 1):
        status = "✓ Completed" if entry.get('done') == True else ("⏰ Timeout" if entry.get('done') == "timeout" else "⏸ Pending")
        project = entry.get('project', '') or "Not specified"
        download_path = entry.get('download_path', '') or "Not specified"
        
        print(f"[{idx:2d}] {entry.get('title', 'No title')}")
        print(f"     Status: {status}")
        print(f"     Project: {project}")
        print(f"     Download: {download_path}")
        print(f"     URL: {entry.get('url', 'N/A')}")
        print()

def update_project():
    """
    Update the project field for a specific database entry.
    Displays the database and allows user to select an entry to modify.
    """
    database = load_database()
    if not database:
        print("The database is empty.")
        return
    
    display_database()
    
    try:
        entry_num = int(input("Entry number to modify (0 to cancel): "))
        if entry_num == 0:
            return
        
        if 1 <= entry_num <= len(database):
            entry = database[entry_num - 1]
            current_project = entry.get('project', '') or "Not specified"
            
            print(f"\nSelected entry: {entry.get('title', 'No title')}")
            print(f"Current project: {current_project}")
            
            new_project = input("New project (Enter to keep current): ").strip()
            if new_project:
                entry['project'] = new_project
                save_database(database)
                print(f"✓ Project updated: '{new_project}'")
            else:
                print("No changes made.")
        else:
            print("Invalid entry number.")
    except ValueError:
        print("Please enter a valid number.")
    except KeyboardInterrupt:
        print("\nOperation cancelled.")

def search_by_project():
    """
    Search and display entries by project name.
    Performs case-insensitive search on project field.
    """
    database = load_database()
    if not database:
        print("The database is empty.")
        return
    
    project_name = input("Project name to search for: ").strip()
    if not project_name:
        return
    
    found_entries = [entry for entry in database if project_name.lower() in entry.get('project', '').lower()]
    
    if found_entries:
        print(f"\n=== RESULTS FOR PROJECT '{project_name}' ({len(found_entries)} entries) ===")
        print("-" * 80)
        
        for idx, entry in enumerate(found_entries, 1):
            status = "✓ Completed" if entry.get('done') == True else ("⏰ Timeout" if entry.get('done') == "timeout" else "⏸ Pending")
            
            print(f"[{idx}] {entry.get('title', 'No title')}")
            print(f"    Status: {status}")
            print(f"    Download: {entry.get('download_path', 'Not specified')}")
            print()
    else:
        print(f"No entries found for project '{project_name}'.")

def main():
    """
    Main menu interface for database management.
    Provides options to view, update, search, and show statistics.
    """
    while True:
        print("\n" + "="*50)
        print("TUNES DATABASE MANAGER")
        print("="*50)
        print("1. Display entire database")
        print("2. Update entry project")
        print("3. Search by project")
        print("4. Statistics")
        print("0. Exit")
        print("-"*50)
        
        try:
            choice = input("Your choice: ").strip()
            
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                display_database()
            elif choice == "2":
                update_project()
            elif choice == "3":
                search_by_project()
            elif choice == "4":
                show_stats()
            else:
                print("Invalid choice. Please try again.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

def show_stats():
    """
    Display statistics about the database contents.
    Shows counts and percentages for different download statuses and project distribution.
    """
    database = load_database()
    if not database:
        print("The database is empty.")
        return
    
    total = len(database)
    completed = len([e for e in database if e.get('done') == True])
    timeout = len([e for e in database if e.get('done') == "timeout"])
    pending = len([e for e in database if e.get('done') == False])
    
    projects = {}
    for entry in database:
        project = entry.get('project', '') or "Not specified"
        projects[project] = projects.get(project, 0) + 1
    
    print(f"\n=== STATISTICS ===")
    print(f"Total entries: {total}")
    print(f"Completed: {completed} ({completed/total*100:.1f}%)")
    print(f"Timeout: {timeout} ({timeout/total*100:.1f}%)")
    print(f"Pending: {pending} ({pending/total*100:.1f}%)")
    
    print(f"\nProjects:")
    for project, count in sorted(projects.items()):
        print(f"  - {project}: {count} entry(ies)")

if __name__ == "__main__":
    main()
