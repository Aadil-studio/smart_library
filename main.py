from controllers.app_controller import LibraryController

def main():
    print("=== Smart Library Management System ===")
    controller = LibraryController()
    
    # Sample execution
    controller.register_book("Software Architecture", "Garlan", "978-1234567890")
    print("Books in System:", controller.list_books())
    
    fine = controller.calculate_member_fine("student", 3)
    print(f"Calculated Fine for 3 days (Student): Rs. {fine}")

if __name__ == "__main__":
    main()