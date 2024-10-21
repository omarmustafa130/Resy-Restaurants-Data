import os
import pandas as pd

# Define the directory containing the Excel files
folder_path = r'C:\Omar\Work\Upwork\Completed\Resy Data\Complete Resy Data'  # Update this with the actual folder path

# Create an empty list to store dataframes
combined_data = []

# Iterate through each file in the folder
for file_name in os.listdir(folder_path):
    if file_name.endswith('.xlsx'):
        # Get the state name from the file name
        state = os.path.splitext(file_name)[0]

        # Load the Excel file
        file_path = os.path.join(folder_path, file_name)
        excel_file = pd.ExcelFile(file_path)

        # Iterate through each sheet in the Excel file (which corresponds to cities)
        for city in excel_file.sheet_names:
            # Read the data from the sheet
            df = pd.read_excel(file_path, sheet_name=city)

            # Add the 'City' and 'State' columns to the dataframe
            df['City'] = city
            df['State'] = state

            # Append the dataframe to the list
            combined_data.append(df)

# Concatenate all the dataframes in the list
final_df = pd.concat(combined_data, ignore_index=True)

# Save the combined dataframe to a CSV file
final_df.to_csv('combined_data.csv', index=False)
