from api import clean_script, create_script_mapping

def test_script_cleaning():
    # Read the original script
    with open('london_travel_script.txt', 'r') as file:
        original_script = file.read()
    
    print("📝 Original Script:")
    print("-" * 80)
    print(original_script)
    print("-" * 80)
    
    # Clean the script
    cleaned_script = clean_script(original_script)
    
    print("\n🧹 Cleaned Script:")
    print("-" * 80)
    print(cleaned_script)
    print("-" * 80)
    
    # Create the mapping
    script_mapping = create_script_mapping(original_script, cleaned_script)
    
    print("\n🗺️ Script Mapping:")
    print("-" * 80)
    for position, bracketed_text in script_mapping.items():
        print(f"Position {position}: {bracketed_text}")
    print("-" * 80)
    
    # Save the cleaned script to a new file
    with open('london_travel_script_cleaned.txt', 'w') as file:
        file.write(cleaned_script)
    
    print("\n✅ Cleaned script saved to 'london_travel_script_cleaned.txt'")

if __name__ == "__main__":
    test_script_cleaning() 