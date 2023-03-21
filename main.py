import cv2
import os
import pathlib
from pick import pick, Option
from configparser import ConfigParser
from cross_stitch_helper import CrossStitchHelper


if __name__ == '__main__':
    config_file = ConfigParser()
    config_file.read('config.ini')

    filename = pathlib.Path(config_file.get('scheme', 'name'))
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Scheme file '{filename}' does not exist!")

    page_filename = filename.stem

    cross_stitch_helper = CrossStitchHelper(filename=filename, config=config_file)
    cross_stitch_helper.create_results_directory()
    cross_stitch_helper.create_thresholds_pickle_if_not_exists()

    colors_found = cross_stitch_helper.find_colors_on_page()

    action = None
    do_not_save = False

    main_menu_actions = [
        Option("Single color - enter single color number", "single"),
        Option("All - generate all images", "all"),
        Option("Exit", "exit")
    ]

    option, index = pick(main_menu_actions, "Choose your action:", indicator="\u25C6")

    if option.value == "all":
        print("Generating all files with default threshold")
        for color in colors_found:
            new_scheme, _ = cross_stitch_helper.prepare_scheme_for_color(color=color)
            new_width = int(new_scheme.shape[1] * 0.2)
            new_height = int(new_scheme.shape[0] * 0.2)
            clone = cv2.resize(new_scheme, (new_width, new_height), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f'{page_filename}/res_{color}_test.png', new_scheme)

    if option.value == "exit":
        print("Exiting without saving changes!")

    if option.value == "single":
        selected_color, _ = pick(["Custom", *colors_found], "Select color:")
        if selected_color == "Custom":
            selected_color = int(input("Please select color number: "))
            if selected_color > cross_stitch_helper.config.getint('template', 'number_of_colors'):
                print(f"Your image contains only {cross_stitch_helper.config.getint('template', 'number_of_colors')} "
                      f"colors.")
        new_scheme, threshold = cross_stitch_helper.prepare_scheme_for_color(color=selected_color)
        original_threshold = threshold
        new_threshold = threshold

        single_color_menu_options = [
            Option("Display preview", "preview"),
            Option("Increase threshold (+0.0075)", "+"),
            Option("Decrease threshold (-0.0075)", "-"),
            Option("Increase threshold (+0.015)", "++"),
            Option("Decrease threshold (-0.015)", "--"),
            Option("Increase threshold (+0.030)", "++++"),
            Option("Decrease threshold (-0.030)", "----"),
            Option("Save - save changes and create file", "save"),
            Option("Exit", "exit")
        ]

        while True:
            option, index = pick(single_color_menu_options,
                                 f"Color: {selected_color} | Current threshold: {new_threshold}\nChoose your action:",
                                 indicator="\u25C6")

            if "+" in option.value:
                increase_value = option.value.count('+') * 0.0075
                new_threshold = threshold + increase_value
                print(f"Increasing threshold by {increase_value} to {new_threshold}")
                new_scheme, threshold = cross_stitch_helper.prepare_scheme_for_color(color=selected_color,
                                                                                     custom_threshold=new_threshold)

            if "-" in option.value:
                decrease_value = option.value.count('-') * 0.0075
                new_threshold = threshold - decrease_value
                print(f"Decreasing threshold by {decrease_value} to {new_threshold}")
                new_scheme, threshold = cross_stitch_helper.prepare_scheme_for_color(color=selected_color,
                                                                                     custom_threshold=new_threshold)


            if option.value == "exit":
                print("Exiting without saving changes!")
                break

            if option.value == "save":
                scale_percent = 20
                new_width = int(new_scheme.shape[1] * 0.2)
                new_height = int(new_scheme.shape[0] * 0.2)
                new_scheme = cv2.resize(new_scheme, (new_width, new_height), interpolation=cv2.INTER_AREA)

                cv2.imwrite(f'{page_filename}/res_{selected_color}_test.png', new_scheme)
                print(f"File saved to: {page_filename}/res_{selected_color}_test.png")
                if original_threshold != new_threshold:
                    print(f"Overriding threshold value for color {selected_color} to {new_threshold}")
                    cross_stitch_helper.override_threshold_for_color(color=selected_color, new_threshold=new_threshold)
                break

            if option.value == "preview":
                print("Preview opened in a new window.\nPress any key to close it.")
                cross_stitch_helper.display_preview(image_to_show=new_scheme)


