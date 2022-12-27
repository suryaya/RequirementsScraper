import os
import pdfplumber
import re


# Global functions
def detect_input_pdfs(self, input_path):
    """Returns a list with filepaths of all pdfs being used in the input"""

    input_pdfs = []

    for file in os.listdir(self.output_path):
        if file.endswith('.pdf'):
            input_pdfs.append(os.path.join(self.input_path, file))

    return input_pdfs


class PdfSettings:
    """ This class provides PDF settings applicable to all pdf manipulation functions and methods."""

    def __init__(self):
        pass

    class TableSettings:
        """ This class stores detection parameters for PDFPlumber. Currently only supports TfNSW table preset (should be
        good enough for most cases """

        def __init__(self):
            self.table_parameters = self.settings()

        @classmethod
        def settings(cls, preset='TfNSW'):

            available_presets = ['TfNSW']

            if preset == 'TfNSW':
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "explicit_vertical_lines": [],
                    "explicit_horizontal_lines": [],
                    "snap_tolerance": 10,
                    "snap_x_tolerance": 10,
                    "snap_y_tolerance": 10,
                    "join_tolerance": 3,
                    "join_x_tolerance": 3,
                    "join_y_tolerance": 3,
                    "edge_min_length": 3,
                    "min_words_vertical": 3,
                    "min_words_horizontal": 1,
                    "keep_blank_chars": False,
                    "text_tolerance": 3,
                    "text_x_tolerance": 3,
                    "text_y_tolerance": 3,
                    "intersection_tolerance": 3,
                    "intersection_x_tolerance": 3,
                    "intersection_y_tolerance": 3,
                }
            try:
                return table_settings
            except UnboundLocalError:
                print(f"Error! No table preset \"{preset}\" exists.")

    class PageMargins:

        """ Set parameters related to page / text layout such as regexes for finding requirements and
        setting page margins"""

        def __init__(self, page):

            self.page_margins = self.page_margins(page)

        @classmethod
        def page_margins(cls, page, preset='TfNSW'):
            width = page.width
            height = page.height

            """ This function takes a pdfplumber page object and returns page margins based on value of `preset`"""
            if preset == 'TfNSW':
                page_margins = (0, 50, width, height - 70)
            try:
                return page_margins
            except UnboundLocalError:
                print(f"Error! No pdf page preset {preset} exists.")


class RequirementsScraper:

    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

    class SearchPatterns:
        def __init__(self, chapter_headings, requirements):
            self.chapter_headings, self.requirements = self.search_patterns()

        @classmethod
        def search_patterns(cls, preset='TfNSW'):
            if preset == 'TfNSW':
                chapter_headings = r"(\n\s*\d[.]?\d?[.]?\d?\s+[A-Z].*)"
                requirements = r"(?sm)^([(]\w{0,4}[)]\s)(.*?)(?=^[(]\w{0,4}[)]\s)"
            try:
                return chapter_headings, requirements
            except UnboundLocalError:
                print(f"Error! No pdf page preset {preset} exists.")

    @staticmethod
    def scrape_pdfs(self, chapter_headings, requirements, table_settings, extract_tables=True, table_resolution=100):

        """Main function to convert document requirements to a dataframe."""
        input_pdfs = self.detect_input_pdfs(self.input_path)

        # Indexes
        table_index = 0

        # Folder for saving images:

        if extract_tables:
            temp_folder = self.output_path()
            if not os.path.exists(table_filepath):
                os.makedirs(table_filepath)

        for input_pdf in input_pdfs:

            pdfreader = pdfplumber.open(self.input_path)
            pages = pdfreader.pages

            for page in pages:

                page_margins = PdfSettings.PageMargins.page_margins(page)

                # Crop header, extract text, locate tables to extract later/ remove text
                page = page.crop(page_margins)
                page_text = page.extract_text()
                tables = page.find_tables()
                tables_bbox = []

                for table in tables:
                    table_index += 1
                    tables_bbox.append(table.bbox)





                for table in tables:
                    # Loop over each table found, add bounding box to list. Create dummy folder for tables
                    table_index += 1
                    tables_bbox.append(table.bbox)
                    table_filename = f"TABLE {table_index}.png"

                    table_filepath = os.path.join(self.input_path, "scrape_temp_folder")
                    page.crop(table.bbox).to_image()

                if extract_tables:
                    pass
                    # Find tables
