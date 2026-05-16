import os
import datetime
import shutil
from datetime import date
from pathlib import Path
from openpyxl import load_workbook
import re  # Used for advanced regex parsing
import time
import platform
import subprocess

from urllib3.util.util import reraise

from photoexperiment import (
    make_square,
    get_photo_details,
    generic_image_request,
    check_llm_status,
    reveal_in_file_manager,
    calculate_days_passed,
    add_row_to_excel
)

# --- Genre classification code
# --- Configuration ---


# created by Sonnet 4.6








def full_upload_process_output(image_path: str, xlsx_path: str, sheet_name: str, row=None, col=None):
    """

    :param image_path:
    :param xlsx_path:
    :param sheet_name:
    :param row:
    :param col:
    :return:
    """
    MODEL_NAME = "gemma4:31b-cloud"

    desc_prompt = (
        "You a professional photography critique. "
        "Describe what you see in this image, in one paragraph. It should be no more than one short sentence. Don't use superlatives"
    )

    genre_prompt = (
        "You are an expert photography critic and genre classifier. "
        "Analyze the provided image and determine the primary genre of photography. "
        "Your output must be concise, descriptive, and contain only the name of the genre (e.g., 'Portraiture', 'Landscape Photography', 'Street Photography'). "
        "Do not provide any preamble, explanation, or filler text."
    )

    keywords_prompt = (
        "You are an expert computer vision assistant. "
        "Analyze this image and list every distinct, primary object you can see. "
        "Respond ONLY with a comma-separated list of object names (e.g., dog, chair, book, window). "
        "Do not include any preamble, explanation, or formatting outside of the comma-separated list."
    )
    location_prompt = (
        "Analyse the image and determine the location. "
        "The output should be strictly formated as country, location, site. "
        "If any of the items cannot be determined, replace it with 'undetermined'. "
        "If thinking time is longer than 300 seconds, output 'undetermined, undetermined, undetermined'."
    )
    llm_status = check_llm_status("ollama", "192.168.10.187")
    img_file_exists = (os.path.isfile(image_path))
    xlsx_file_exists = os.path.isfile(xlsx_path)
    if llm_status["online"] and img_file_exists: #
        exif_data = get_photo_details(image_path)
        padded_file_name = make_square(image_path)
        reveal_in_file_manager(image_path)
        genre = generic_image_request(image_path, "gemma4", genre_prompt)
        desc = generic_image_request(image_path, "gemma4", desc_prompt)
        keywords_raw = generic_image_request(image_path, "gemma4", keywords_prompt)
        location = generic_image_request(image_path, "gemma4:31b-cloud", location_prompt)

        print(f"Padded file: {padded_file_name}")
        if genre:
            exif_data["Genre"] = str(genre)
            print("Genre:")
            print(genre)
        else:
            print("Genre was not determined")

        if exif_data:
            print("EXIF Data:")
            for key, value in exif_data.items():
                print(f"{value}", end="\t")
            print('\n')
        else:
            print("EXIF data could not be extracted.")

        if desc:
            print("Description:")
            print(desc)
        else:
            print("Description could not be generated.")
        if location:
            print(f"Location: {location}")
        else:
            print("Location could not be determined.")

        if keywords_raw:
            keywords_list = [k.strip() for k in keywords_raw.split(',') if k.strip()]
            print("Keywords:")
            for k in keywords_list:
                print(f"{k}", end="\t")
        else:
            print("No keywords were found.")
        print('\n')

        if os.path.isfile(xlsx_path):
            print(f"XLSX file {xlsx_path} found. Attempting to write data...")
            # create a list to add to the Excel file
            valueslist = [
                exif_data.get("Camera", ""),
                exif_data.get("Lens", ""),
                float(exif_data.get("FL", 0)),  # Get only the focal length number
                float(exif_data.get("EFL", 0)),  # Get only the effective focal length number
                exif_data.get("Genre", ""),
                datetime.datetime.strptime(exif_data.get("Date Taken", ""), "%Y-%m-%d"),
                datetime.datetime.strptime(exif_data.get("Date Posted", ""), "%Y-%m-%d"),
                exif_data.get("Day Of Week", ""),
                datetime.datetime.strptime(exif_data.get("Time Posted", ""), "%H:%M:%S"),
                location,
                image_path
            ]
            if desc:
                valueslist.append(desc)
            else:
                valueslist.append(" ")
            if keywords_raw:
                for k in keywords_list:
                    valueslist.append(k)
            else:
                valueslist.append(" ")
            # Update the Excel file with the new row of data
            add_row_to_excel(file_name=xlsx_path,
                             sheet_name=sheet_name,
                             values=valueslist,
                             row_number=row, col_number=col)
            return "Excel updated successfully."
        else:
            print(f"Excel file {xlsx_path} not found. Data will not be saved to Excel.")
            return "Failed to update Excel."
    else:
        reasons = ""
        if not file_exists:
            print(f"Image file {image_path} not found.")
            reasons = "Image file not found "
        if not llm_status["online"]:
            print(f"LLM service not online.")
            reasons += "LLM service not online."
        return f"Update failed. Reasons: {reasons}"


# --- Main Execution Block ---
if __name__ == "__main__":
    # --- CONFIGURATION ---
    start_time = time.perf_counter()
    image_to_process = r"D:\pictures\2024\08\03 TLV beach with Sharon\Devs\DSC00534.jpg"
    xlsx_file = r"G:\My Drive\Per Day 2026\One Photo per day 2026-2027.xlsx"
    xl_sheet = "Photos"

    row = calculate_days_passed(2026, 4, 11) + 2  # days since 2026-04-11 plus 2 header rows
    update_status = full_upload_process_output(image_to_process, xlsx_file, xl_sheet, row=row)
    print(update_status)

    end_time = time.perf_counter()
    print(f"The entire batch operation took {end_time - start_time:4f} seconds.")

    #print(check_llm_status("ollama","192.168.10.187"))
"""
#--Test section
    img_files =[
        r"D:\pictures\2011\11\27 Eva 2011\devs\IMG_5669.jpg",
        r"D:\pictures\2024\05\07 Ireland\Devs\IMG_2964.jpg",
        r"D:\pictures\2021\03\27 Masada\devs\IMG_8029.jpg",
        r"F:\Pictures\2025\10\15 Dolomites\Devs\IMT_3504.jpg",
        r"D:\pictures\2020\06\05 Tel Aviv at night\devs\BO9A6739.jpg",
        r"D:\pictures\2021\06\12 Phtototips Desert\devs\IMG_1962.jpg",
        r"D:\pictures\2025\02\08 Phtototips Swing\Devs\IMT_5537.jpg",
        r"D:\pictures\2018\06\21 Kids sunset\devs\DSC01006.jpg",
        r"D:\pictures\2021\10\2021-10-25 Romania day 1\devs\IMG_2706.jpg",
        r"F:\Pictures\2025\12\2025-12-19 TLV with Boris\Devs\DSC03006.jpg",
        r"F:\Pictures\2025\08\23 Desert Night\Devs\DSC01989.jpg",
        r"F:\Pictures\2025\08\23 Desert Night\Devs\IMT_6004.jpg",
        r"F:\Pictures\2025\10\21 Kobarid\Devs\IMT_5177.jpg",
        r"F:\Pictures\2025\10\14 Dolomites\Devs\IMT_3080.jpg",
        r"F:\Pictures\2025\09\2025-09-07 Lunar Ecplise\Devs\IMT_6370.jpg",
        r"D:\pictures\2008\08\redbullrace\select\devs\IMG_1022.jpg",
        r"D:\pictures\2017\12\12 Prague\devs\IMG_3632.jpg",
        r"D:\pictures\2025\2025-05-26 Tatras\Devs\IMG_6971.jpg"
    ]


    model="gemma4:31b"
    prompt =  (
        "You're a professional photography teacher. "
        "Rank the following photo using four categories: composition, storytelling, aesthetics and technical quality. "
        "Output the grade as a combined grade and each of the elements of the grade individually."
        "Format strictly as numbers: composition, storytelling, aesthetics, technical quality, overall grade." )
    results = []
    start_time = time.perf_counter()
    for e, i in enumerate(img_files):
        print(f"Working on image {e}")
        rawres = generic_image_request(i, model, prompt)
        print(rawres)
        results.append(rawres)
    end_time = time.perf_counter()
    for e, r in enumerate(results):
        lst = r.split(",")
        print(e,'\t')

        for l in lst:
            print(l, end="\t")
        print('\n')

    end_time = time.perf_counter()
    print(f"The entire batch operation took {end_time-start_time:4f} seconds using.")

"""







