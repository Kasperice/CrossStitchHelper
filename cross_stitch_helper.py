from typing import List, Tuple

import cv2
import os
import pickle
import numpy as np


class CrossStitchHelper:
    def __init__(self, filename, config):
        self.config = config
        self.filename = filename.stem
        self.template = cv2.imread(self.config.get("template", "name"))
        self.scheme = self.open_and_resize_scheme()
        self.template_coordinates = self.create_template_coordinates()

    def create_thresholds_pickle_if_not_exists(self) -> None:
        """
        Creates thresholds.p file (if not created before).
        File will contain default threshold value for each color.
        :return: None
        """
        if not os.path.exists("thresholds.p"):
            print("File thresholds.p not found, creating new one.")
            thresholds = {
                i: 0.60
                for i in range(
                    1, self.config.getint("template", "number_of_colors") + 1
                )
            }
            pickle.dump(thresholds, open("thresholds.p", "wb"))

    def create_results_directory(self) -> None:
        """
        Prepares directory for saving result files.
        :return: None
        """
        if not os.path.isdir(self.filename):
            os.makedirs(self.filename)

    @staticmethod
    def override_threshold_for_color(color: int, new_threshold: float) -> None:
        """
        Replaces old threshold value with a new one.
        :param color: Color number for which threshold should be changed.
        :param new_threshold: New threshold value.
        :return: None
        """
        to_be_changed = pickle.load(open("thresholds.p", "rb"))
        to_be_changed[color] = new_threshold
        pickle.dump(to_be_changed, open("thresholds.p", "wb"))

    @staticmethod
    def display_preview(image_to_show) -> None:
        """
        Displays image in a new window. Waits for any key press to close.
        :param image_to_show: Image to be displayed.
        :return:
        """
        cv2.namedWindow("image")
        cv2.imshow("image", image_to_show)
        cv2.waitKey(0)
        cv2.destroyWindow("image")
        cv2.waitKey(1)

    def create_template_coordinates(
        self,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Prepares list of coordinates basing on config file data.
        :return: List with symbols coordinates for template
        """
        template_parameters = dict(self.config.items("template"))

        coords = [
            (x, y)
            for x in range(int(template_parameters["y"]))
            for y in range(int(template_parameters["x"]))
        ][: int(template_parameters["number_of_colors"])]

        x_offset = int(template_parameters["x_offset"])
        y_offset = int(template_parameters["y_offset"])
        sample_width = int(template_parameters["sample_width"])

        new_coords = []
        for x, y in coords:
            a = y_offset + x * (sample_width + 2 * y_offset)
            b = x_offset + y * (sample_width + 2 * x_offset)
            new_coords.append(((a, a + sample_width), (b, b + sample_width)))

        return new_coords

    def open_and_resize_scheme(self):
        """
        Opens and resizes scheme image.
        :return: Scheme resized to size used for image recognition.
        """
        image = cv2.imread(f"{self.filename}.png")
        scale_percent = 137 / self.config.getint("scheme", "sample_width")
        new_width = int(image.shape[1] * scale_percent)
        new_height = int(image.shape[0] * scale_percent)
        return cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
        )

    def find_colors_on_page(self) -> List:
        """
        Returns all colors used on page.
        If pickle file is not available colors will be searched on scheme using search_for_colors_on_page function.
        :return: Content of colors.p file.
        """
        if not os.path.exists(f"{self.filename}_colors.p"):
            print(
                "File containing colors on this page was not found.\n"
                "New will be created in a while, please wait..."
            )
            self.search_for_colors_on_page()

        return pickle.load(open(f"{self.filename}_colors.p", "rb"))

    def crop_template(self, coordinate: Tuple[Tuple[int, int], Tuple[int, int]]):
        """
        Crops template file to extract single symbol.
        :param coordinate: Coordinates of single symbol.
        :return: Single symbol image
        """
        cropped_template = self.template[
            coordinate[0][0] : coordinate[0][1], coordinate[1][0] : coordinate[1][1]
        ]

        scale_percent = 110 / self.config.getint("template", "sample_width")
        new_width = int(cropped_template.shape[1] * scale_percent)
        new_height = int(cropped_template.shape[0] * scale_percent)
        return cv2.resize(
            cropped_template, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
        )

    def search_for_colors_on_page(self) -> None:
        """
        Looks for colors available on scheme and prepares pickle file with all found colors.
        :return: None
        """
        found = []
        for color_id, coordinates in enumerate(self.template_coordinates, start=1):
            cropped_template = self.crop_template(coordinates)

            scheme_gray = cv2.cvtColor(self.scheme, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(cropped_template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(scheme_gray, template_gray, cv2.TM_CCOEFF_NORMED)

            thresholds = pickle.load(open("thresholds.p", "rb"))
            threshold = thresholds[color_id]

            (startY, startX) = np.where(result >= threshold)
            if len(startX) == len(startY) != 0:
                found.append(color_id)

        pickle.dump(found, open(f"{self.filename}_colors.p", "wb"))

    def prepare_scheme_for_color(self, color: int, custom_threshold=None) -> Tuple:
        """
        Prepares scheme for specified color.
        :param color: Color number
        :param custom_threshold: Threshold to be used. If None threshold will be read from pickle file.
        :return: Scheme with all symbols found, threshold used
        """
        for color_id, coordinates in enumerate(
            self.template_coordinates[color - 1 : color], start=1
        ):
            cropped_template = self.crop_template(coordinates)

            (tH, tW) = cropped_template.shape[:2]

            scheme_gray = cv2.cvtColor(self.scheme, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(cropped_template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(scheme_gray, template_gray, cv2.TM_CCOEFF_NORMED)

            if custom_threshold is None:
                threshold = pickle.load(open("thresholds.p", "rb"))[color]
            else:
                threshold = custom_threshold

            (found_y, found_x) = np.where(result >= threshold)

            modified_scheme = self.scheme.copy()

            for x, y in zip(found_x, found_y):
                cv2.rectangle(
                    modified_scheme, (x, y), (x + tW, y + tH), (0, 0, 255), 12
                )

            return modified_scheme, threshold
