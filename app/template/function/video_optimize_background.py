import os
import copy
import shutil

from PIL import Image
import tkinter
from tkinter import filedialog

from customtkinter import CTkButton, CTkFrame, CTkLabel, CTkEntry, CTkComboBox

from app.tailorwidgets.tailor_modal import TLRModal
from app.tailorwidgets.tailor_message_box import TLRMessageBox
from app.tailorwidgets.default.filetypes import VIDEO_EXTENSION, IMAGE_VIDEO_FILETYPES

from app.utils.paths import Paths
from app.src.utils.timer import Timer
from app.config.config import Config
from app.src.utils.logger import Logger

from app.src.algorithm.video_optimize_background.video_optimize_background import change_background


def alg_video_optimize_background(work):
    work._clear_right_frame()
    # Ensure that there is operational video
    video_path = work.video.path
    if not os.path.exists(video_path) or os.path.splitext(video_path)[1] not in VIDEO_EXTENSION:
        message_box = TLRMessageBox(work.master,
                                    icon="warning",
                                    title=work.translate("Warning"),
                                    message=work.translate("Please import the video file you want to process first."),
                                    button_text=[work.translate("OK")],
                                    bitmap_path=os.path.join(Paths.STATIC, work.appimages.ICON_ICO_256))
        work.dialog_show(message_box)
        return

    timestamp = Timer.get_timestamp()
    operation_file = os.path.join(work.app.project_path, "files", timestamp)
    os.makedirs(operation_file, exist_ok=True)
    log_path = os.path.join(operation_file, f"{timestamp}.log")

    video_name = f"{Config.OUTPUT_VIDEO_NAME}{os.path.splitext(work.video.path)[1]}"
    pre_last_video_name = f"pre_{Config.OUTPUT_VIDEO_NAME}{os.path.splitext(work.video.path)[1]}"
    output_video_path = os.path.join(work.app.project_path, Config.PROJECT_VIDEOS, video_name)
    pre_last_video_path = os.path.join(work.app.project_path, Config.PROJECT_VIDEOS, pre_last_video_name)
    if os.path.exists(output_video_path):
        if os.path.exists(pre_last_video_path):
            os.remove(pre_last_video_path)
        os.rename(output_video_path, pre_last_video_path)
        work.video.path = pre_last_video_path
    else:
        pre_last_video_path = work.video.path

    work._right_frame.grid_columnconfigure(0, weight=1)
    work._right_frame.grid_rowconfigure((0, 1, 2, 3, 5), weight=1)
    work._right_frame.grid_rowconfigure(4, weight=100)

    # Image Path
    image_label = CTkLabel(master=work._right_frame,
                           fg_color="transparent",
                           text=work.translate("Please enter the image path:"))
    image_label.grid(row=0, column=0, pady=(5, 0), sticky="w")

    image_frame = CTkFrame(master=work._right_frame,
                           fg_color=work._apply_appearance_mode(work._fg_color),
                           bg_color=work._apply_appearance_mode(work._fg_color),
                           )
    image_entry_var = tkinter.StringVar(value="")
    image_entry = CTkEntry(master=image_frame,
                           textvariable=image_entry_var,
                           state="disabled",
                           )
    image_entry.grid(row=0, column=0, padx=(10, 0), sticky="w")

    background_type = "image"
    video_combo_var = tkinter.StringVar(value=work.translate("Repeat"))

    def _browse_event(event=None):
        entry_image_path = filedialog.askopenfilename(parent=work, filetypes=IMAGE_VIDEO_FILETYPES[work.language])
        try:
            image_entry_var.set(entry_image_path)
        except:
            image_entry_var.set("")
        flag = False
        lower_entry_image_path = entry_image_path.lower()
        for video_ext in VIDEO_EXTENSION:
            if lower_entry_image_path.endswith(video_ext):
                flag = True
                nonlocal background_type
                background_type = "video"
                break
        if flag:
            video_frame = CTkFrame(master=work._right_frame,
                                   fg_color=work._apply_appearance_mode(work._fg_color),
                                   bg_color=work._apply_appearance_mode(work._fg_color),
                                   )
            video_label = CTkLabel(master=video_frame,
                                    fg_color="transparent",
                                    text=work.translate("Video Alignment Method:"))
            video_label.grid(row=0, column=0, sticky="w")

            def video_combobox_callback(choice):
                video_combo_var.set(choice)

            video_align_combobox = CTkComboBox(master=video_frame,
                                          values=[
                                              work.translate("Repeat"),
                                              work.translate("Align"),
                                          ],
                                          command=video_combobox_callback,
                                          variable=video_combo_var)
            video_align_combobox.grid(row=1, column=0, sticky="ew", padx=10)
            video_frame.grid(row=3, column=0, sticky="new")

    image_browse_button = CTkButton(master=image_frame,
                                    width=80,
                                    text=work.translate("Browse"),
                                    command=_browse_event)
    image_browse_button.grid(row=0, column=1, padx=(10, 10), sticky="ne")
    image_frame.grid(row=1, column=0, pady=(5, 0), sticky="w")

    # Resize Style
    resize_frame = CTkFrame(master=work._right_frame,
                            fg_color=work._apply_appearance_mode(work._fg_color),
                            bg_color=work._apply_appearance_mode(work._fg_color),
                            )
    resize_label = CTkLabel(master=resize_frame,
                            fg_color="transparent",
                            text=work.translate("Picture Position:"))
    resize_label.grid(row=0, column=0, sticky="w")
    resize_combo_var = tkinter.StringVar(value=work.translate("Fill"))

    def combobox_callback(choice):
        resize_combo_var.set(choice)

    resize_combobox = CTkComboBox(master=resize_frame,
                                  values=[
                                      work.translate("Fill"),
                                      work.translate("Center"),
                                      work.translate("Left-Top"),
                                      work.translate("Left-Down"),
                                      work.translate("Right-Top"),
                                      work.translate("Right-Down"),
                                      work.translate("Top-Center"),
                                      work.translate("Down-Center"),
                                      work.translate("Left-Center"),
                                      work.translate("Right-Center"),
                                  ],
                                  command=combobox_callback,
                                  variable=resize_combo_var)
    resize_combobox.grid(row=1, column=0, sticky="w", padx=10)
    resize_frame.grid(row=2, column=0, sticky="w")

    def _video_change_background():
        origin_background_path = image_entry_var.get()

        temp_matting_video = os.path.join(operation_file, "matte.mp4")

        background_path = os.path.join(operation_file, f"background.{os.path.splitext(origin_background_path)[1]}")
        shutil.copy(origin_background_path, background_path)

        resize_types = {
            work.translate("Fill"): "resize",
            work.translate("Center"): "center",
            work.translate("Left-Top"): "left-top",
            work.translate("Left-Down"): "left-down",
            work.translate("Right-Top"): "right-top",
            work.translate("Right-Down"): "right-down",
            work.translate("Top-Center"): "top-center",
            work.translate("Down-Center"): "down-center",
            work.translate("Left-Center"): "left-center",
            work.translate("Right-Center"): "right-center",
        }
        resize_type = resize_types[resize_combo_var.get()]

        video_align_types = {
            work.translate("Repeat"): "repeat",
            work.translate("Align"): "align",
        }
        align_type = video_align_types[video_combo_var.get()]

        input_data = {
            "config": {
                "device": work.device,
                "model-type": "webcam",
            },
            "input": {
                "timestamp": timestamp,
                "log_path": log_path,
                "result_type": "compose",  # foreground/matte/compose
                "video_path": pre_last_video_path,
                "background_type": background_type,
                "background": background_path,
                "resize": resize_type,
                "align": align_type,
            },
            "output": {
                "video_path": temp_matting_video,
                "output_path": output_video_path,
            }

        }

        change_background(input_data)

    def _video_change_background_modal():
        if not os.path.exists(image_entry_var.get()):
            message_box = TLRMessageBox(work.master,
                                        icon="warning",
                                        title=work.translate("Warning"),
                                        message=work.translate("Please enter a valid image path."),
                                        button_text=[work.translate("OK")],
                                        bitmap_path=os.path.join(Paths.STATIC, work.appimages.ICON_ICO_256))
            work.dialog_show(message_box)
            return
        logger = Logger(log_path, timestamp)
        TLRModal(work,
                 _video_change_background,
                 fg_color=(Config.MODAL_LIGHT, Config.MODAL_DARK),
                 logger=logger,
                 translate_func=work.translate,
                 error_message=work.translate("An error occurred, please try again!"),
                 messagebox_ok_button=work.translate("OK"),
                 messagebox_title=work.translate("Warning"),
                 bitmap_path=os.path.join(Paths.STATIC, work.appimages.ICON_ICO_256)
                 )

        work.video.path = output_video_path
        update_video = copy.deepcopy(work.video)
        update_video.path = update_video.path.replace(work.app.project_path, "", 1)
        work.video_controller.update([update_video])
        # update the cut video
        work._video_frame.set_video_path(work.video.path)
        work._clear_right_frame()

    change_background_button = CTkButton(
        master=work._right_frame,
        border_width=0,
        text=work.translate("Background Change"),
        command=_video_change_background_modal,
        anchor="center"
    )
    change_background_button.grid(row=5, column=0, pady=(10, 10), sticky="s")
