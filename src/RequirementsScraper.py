import os
import pdfplumber
from common import *
import re
import pandas as pd
import openpyxl

reserved_table_keyword = 'REServed_table'


# Helper functions
def _extract_table_text(page, table):
    table_text = page.crop(table.bbox).extract_text()
    return table_text


def _remove_table_text(page_text, table_text, table_number):
    updated_text = page_text.replace(table_text, f".\n{reserved_table_keyword} TABLE {table_number}.png.\n")
    return updated_text


def _table_to_image(page, table, table_number, save_location, table_resolution=100, img_extension='png'):
    table_filepath = os.path.join(save_location, f"TABLE {table_number}.{img_extension}")
    page.crop(table.bbox).to_image(resolution=table_resolution).save(table_filepath)


def _create_df(doc_col, heading1_col, heading2_col, requirement_col):
    return pd.DataFrame(columns=[str(doc_col), str(heading1_col), str(heading2_col), str(requirement_col)])


def _req_under_heading(
        previous_heading_tuple, current_heading_tuple, requirement_tuple, last_heading=False
):
    """Function checks if the requirement sits after previous_heading and before current_heading."""
    if last_heading:
        if requirement_tuple[0] > current_heading_tuple[1]:
            return True
    else:
        if previous_heading_tuple[1] < requirement_tuple[0] < current_heading_tuple[1]:
            return True
        else:
            return False


def _find_img_name_in_cell(cell,
                           img_extension='.png'
                           ):
    a = cell.value.find(reserved_table_keyword) + len(reserved_table_keyword)
    b = cell.value.find(img_extension) + len(img_extension)

    img_name = cell.value[a:b].strip()

    return img_name


def _insert_img_to_cell(img_dir,
                        cell_text,
                        cell,
                        ws
                        ):
    img = openpyxl.drawing.image.Image(img_dir)
    img.anchor = str(cell.coordinate)
    ws.add_image(img)


def _post_process_sheet(
        sheet_dir,
        extract_tables=True,
        img_folder=None,
        table_text='Inserted_Table'
):
    wb = openpyxl.load_workbook(sheet_dir)
    ws = wb.active
    if extract_tables and img_folder is None:
        raise ValueError('Require a directory for table_folder if extract_tables is True.')

    # Replace reserved table keyword with an image of the table...

    for row in ws.rows:
        for cell in row:
            if cell.value is not None:
                if reserved_table_keyword in str(cell.value):
                    if extract_tables:
                        img_name = _find_img_name_in_cell(cell)
                        img_dir = os.path.join(img_folder, img_name)
                        _insert_img_to_cell(img_dir, table_text, cell, ws)
                cell.value = str(cell.value).replace(reserved_table_keyword, table_text)
    wb.save("dataframe.xlsx")


def _df_to_excel(df, output_file, extract_tables=False):
    temp_image_folder = os.getcwd()

    delete_file(output_file)
    df.to_excel(output_file)
    _post_process_sheet(output_file, extract_tables=extract_tables, img_folder=temp_image_folder)


# Methods to be accessed via the RequirementsScraper class

def requirement_patterns(preset='General'):
    available_presets = ["General", "TfNSW"]

    if preset in available_presets:

        requirements = ""

        if preset == "General":
            requirements = r"(?sm)^\s*([A-Z]\D|[(]\w*[)]).*?([.:;]\s*\n)"
        if preset == "TfNSW":
            requirements = r"(?sm)^([(]\w{0,4}[)]\s)(.*?)(?=^[(]\w{0,4}[)]\s)"
        return requirements
    else:
        print(f"Search pattern preset {preset} not found!")
        return None


def heading_patterns(preset="TfNSW"):
    """Returns a string that matches headings which may be compiled into
    a regex object"""
    available_presets = ["TfNSW", "RMS QA SPEC"]

    if preset in available_presets:
        chapter_headings = ""

        if preset == "TfNSW":
            chapter_headings = r"(\s*\n\s*\d[.]?\d?[.]?\d?\s+[A-Z].*)"

        if preset == "RMS QA SPEC":
            chapter_headings = r"(?m)((^\s*[A-Z]\d)|(^\d[.]?))([^\n].*)"

        return chapter_headings
    else:
        print(f"Search pattern preset {preset} not found!")
        return None


class Scraper:
    def __init__(self, input_pdf):
        self._input_path = input_pdf

        # Dataframe Columns
        self.__doc_col = "Document"
        self.__heading1 = "Heading 1"
        self.__heading2 = "Heading 2"
        self.__requirement = "Requirement Text"

        # Temporary folder for saving images

        self.__temp_image_folder = os.getcwd()

    def scrape_pdf(
            self,
            headings_str,
            requirements_str,
            # table_settings,
            extract_tables=True,
            page_margins_preset='TfNSW'
    ):
        """Main function to convert document requirements to a dataframe."""
        # Initiate DataFrame

        doc_col = "Document"
        heading_col = "Heading"
        requirement_col = "Requirement Text"

        df = _create_df(self.__doc_col, self.__heading1, self.__heading2, self.__requirement)

        # Indexes / variables
        table_index = 0
        all_text = ""

        # Folder for saving images:

        if extract_tables:

            if not os.path.exists(self.__temp_image_folder):
                os.makedirs(self.__temp_image_folder)

        # Main function
        pdfreader = pdfplumber.open(self._input_path)
        pages = pdfreader.pages

        for page in pages:

            page_margins = pdf_page_margins(page, preset=page_margins_preset)

            # Crop header, extract text, locate tables to extract
            # later/remove text
            page = page.crop(page_margins)
            page_text = page.extract_text()
            tables = page.find_tables()

            # Extract text from page, remove text from page, extract table
            # to image if extract_tables=True, add to all_text
            for table in tables:
                table_index += 1
                table_text = _extract_table_text(page, table)
                page_text = _remove_table_text(page_text, table_text, table_index)

                if extract_tables:
                    _table_to_image(page, table, table_index, self.__temp_image_folder)
            all_text += page_text

        # Find compile search strings into regex
        all_text = remove_cid_text(all_text)

        headings_re = re.compile(headings_str)
        requirements_re = re.compile(requirements_str)

        # Empty lists to hold match positions and text

        headings = []
        requirements = []

        # Return tuples with start position, end position and the text of matches as tuple[0],[1],[2] respectively.

        for match in headings_re.finditer(all_text):
            headings.append((match.start(), match.end(), match.group()))

        for match in requirements_re.finditer(all_text):
            requirements.append((match.start(), match.end(), match.group()))
        # Write to dataframe

        for i, current_heading in enumerate(headings):
            if i == 0:  # Skip first heading as no previous heading exists
                continue

            previous_heading = headings[i - 1]

            for requirement in requirements:
                last_heading = i == len(headings) - 1
                df = self._append_to_df(
                    df,
                    previous_heading,
                    current_heading,
                    requirement,
                    last_heading=last_heading
                )

        return df

    @staticmethod
    def df_to_excel(df, output_file, extract_tables=False):
        """Convert requirements dataframe to Excel file. Only
        use after generating dataframe using scrape_pdf()
        Overwrites output_file."""

        _df_to_excel(df, output_file, extract_tables=extract_tables)

    def _append_to_df(self,
                      df,
                      previous_heading_tuple,
                      current_heading_tuple,
                      requirement_tuple,
                      last_heading=False,
                      ):
        """Writes the doc name, heading and requirement to dataframe in accordance with their positions. Treats
        last heading separately"""
        df_concat = df
        doc_name = os.path.basename(self._input_path)

        requirement_text = requirement_tuple[2].replace("\n", " ")
        if last_heading:
            if requirement_tuple[0] > current_heading_tuple[0]:
                heading_text = current_heading_tuple[2]
                new_row = pd.DataFrame(
                    {self.__doc_col: [doc_name], self.__heading1: [heading_text], self.__heading2: [""],
                     self.__requirement: [requirement_text]})

                df_concat = pd.concat([df, new_row])

        else:
            if previous_heading_tuple[0] < requirement_tuple[0] < current_heading_tuple[0]:
                heading_text = previous_heading_tuple[2]
                new_row = pd.DataFrame(
                    {self.__doc_col: [doc_name], self.__heading1: [heading_text], self.__heading2: [""],
                     self.__requirement: [requirement_text]})

                df_concat = pd.concat([df, new_row])

        return df_concat

    def dump_text(self, page_margins_preset='TfNSW'):
        all_text = ""
        table_index = 0

        pdf = pdfplumber.open(self._input_path)
        pages = pdf.pages

        for page in pages:
            # Crop header, extract text, locate tables to extract
            # later/remove text
            page_margins = pdf_page_margins(page, page_margins_preset)
            page = page.crop(page_margins)
            page_text = page.extract_text()
            tables = page.find_tables()

            # Extract text from page, remove text from page, extract table
            # to image if extract_tables=True, add to all_text
            for table in tables:
                table_index += 1
                table_text = _extract_table_text(page, table)
                page_text = _remove_table_text(page_text, table_text, table_index)
            all_text += page_text
        all_text = remove_cid_text(all_text)
        return all_text