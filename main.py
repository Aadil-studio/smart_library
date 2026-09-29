from controllers.app_controller import LibraryController

def main():
    print("=== Smart Library Management System ===")
    
    # 1. Controller Object Create Karein
    controller = LibraryController()
    
    # 2. Book Register Karein
    controller.register_book("Software Architecture", "Garlan", "978-9999999999")
    
    # 3. All Books Display Karein
    print("\nBooks in System:")
    print(controller.list_books())
    
    # 4. Fine Calculate Karein
    fine = controller.calculate_member_fine("student", 3)
    print(f"\nCalculated Fine for 3 days (Student): Rs. {fine}")

if __name__ == "__main__":
    main()