# -*- coding:utf-8 -*-

import pandas as pd
from datetime import datetime
import os


class Store(object):
    """
    Store dataframe
    :param data: dataframe,
    :param name: str,
    :param path: str,
    :return: none
    """

    def __init__(self, data=None, name=None, path=None):
        if isinstance(data, pd.DataFrame):
            self.data = data
        else:
            raise RuntimeError("data type is incorrect")
        self.name = name
        self.path = path

    def save(self, filename=None):
        """
        Save dataframe to CSV file
        :param filename: str, optional filename. If not provided, uses self.name or auto-generated name
        """
        # Determine the filename to use
        if filename:
            save_name = filename
        elif self.name:
            save_name = self.name
        else:
            save_name = f'{datetime.now().strftime("%Y%m%d-%H%M%S")}'

        # Ensure filename has .csv extension
        if not save_name.endswith(".csv"):
            save_name += ".csv"

        # Determine the full file path
        if (self.path is None) or (self.path == ""):
            file_path = save_name
        else:
            try:
                # Create directory if it doesn't exist
                if not os.path.exists(self.path):
                    os.makedirs(self.path)

                # Join path components
                file_path = os.path.join(self.path, save_name)
            except Exception as e:
                print(f"Error creating directory: {e}")
                file_path = save_name  # Fallback to current directory

        try:
            # Save the dataframe
            self.data.to_csv(file_path, index=False)
            print(f"Data saved successfully to: {file_path}")
            return file_path
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
