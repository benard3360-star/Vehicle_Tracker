import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from django.core.management import call_command

class ExcelFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_file and event.src_path.endswith('.xlsx'):
            print(f"New Excel file detected: {event.src_path}")
            time.sleep(2)  # Wait for file to be fully written
            call_command('load_excel_data')

def start_file_watcher():
    event_handler = ExcelFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path='Data', recursive=False)
    observer.start()
    print("File watcher started for Data folder")
    return observer