import base64
import threading
import os
import sys
import time
import csv
import datetime
import cv2
import flet as ft


def duplicate_rename(file_path):
    if os.path.exists(file_path):
        name, ext = os.path.splitext(file_path)
        i = 1
        while True:
            # 数値を3桁などにしたい場合は({:0=3})とする
            new_name = f"{name}({i}){ext}"
            if not os.path.exists(new_name):
                return new_name
            i += 1
    else:
        return file_path


class CameraCaptureControl(ft.UserControl):
    def __init__(self):
        super().__init__()

        FPS = 30
        FOURCC = "MJPG"
        WIDTH = 1280
        HEIGHT = 720

        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*FOURCC))
        self.capture.set(cv2.CAP_PROP_FPS, FPS)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.recording = False
        self.video_writer = None

        print(f"width: {self.width} height: {self.height}")
        print(f"fps: {self.capture.get(cv2.CAP_PROP_FPS)}")

    def generate_writer(self):
        FOURCC = "avc1"
        VIDEO_EXT = "mp4"

        now = datetime.datetime.now()
        self.now_str = now.strftime("%Y-%m-%d_%H.%M.%S")
        save_filename = f"{self.now_str}_video.{VIDEO_EXT}"
        save_path = os.path.join(SAVE_FOLDER_PATH, save_filename)

        # VideoWriter作成
        fourcc = cv2.VideoWriter_fourcc(*FOURCC)
        return cv2.VideoWriter(save_path, fourcc, self.fps, (self.width, self.height))

    def did_mount(self):
        self.running = True
        self.thread = threading.Thread(target=self.update_frame, args=(), daemon=True)
        self.thread.start()

    def will_unmount(self):
        self.running = False

    def start_record(self):
        self.frame_num = 0
        self.record_time = []
        self.video_writer = self.generate_writer()
        self.recording = True

    def end_record(self):
        self.recording = False

    def save_frame(self):
        while True:
            if self.video_writer is not None:
                if self.recording:
                    if not self.q.empty():
                        frame = self.q.get()
                        self.video_writer.write(frame)  # フレームを書き込む。
                        self.frame_num += 1

    def update_frame(self):
        self.record_time = []
        while self.capture.isOpened() and self.running:
            cap_success, self.raw_frame = self.capture.read()

            if cap_success:
                draw_frame = cv2.resize(self.raw_frame, (640, 360))
                _, draw_frame = cv2.imencode(".jpg", draw_frame, (cv2.IMWRITE_JPEG_QUALITY, 50))
                data = base64.b64encode(draw_frame)
                self.image_control.src_base64 = data.decode()
                self.update()

                if self.video_writer is not None:
                    if self.recording:
                        start_time = time.time()
                        self.video_writer.write(self.raw_frame)  # フレームを書き込む。
                        # print(f"write time: {time.time() - start_time}")
                        self.frame_num += 1
                        self.record_time.append(time.time())

                    else:
                        self.video_writer.release()
                        self.video_writer = None
                        during_time = self.record_time[-1] - self.record_time[0]
                        print(f"record_time: {during_time} frame_num:{self.frame_num} fps: {self.frame_num / during_time}")

    def build(self):
        self.image_control = ft.Image(width=640, height=360, fit=ft.ImageFit.FIT_WIDTH)
        return self.image_control


class Marker:
    def __init__(self, page: ft.Page) -> None:
        self.marker = []
        self.dlg_modal = None
        self.page = page
        self.dlg_count = 0
        self.marked_frame_num = None

    def mark(self, frame_num, marker_name):
        self.marker.append([frame_num, marker_name])

    def save(self, path=duplicate_rename("./marker.csv")):
        with open(path, mode="w", newline="\n") as o_f:
            writer = csv.writer(o_f)

            header = ["frame", "marker_name"]
            writer.writerow(header)

            writer.writerows(self.marker)

        self.marker = []
        self.dlg_count = 0
        self.marked_frame_num = None

    def generate_dlg_modal(self):
        self.dlg_count += 1
        self.dlg_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("マーカー"),
            content=ft.Text("マーカーをセットしました．マーカー名を入力してください．"),
            actions=[
                ft.TextField(label="マーカー名", value=f"marker{self.dlg_count}"),
                ft.TextButton("OK", on_click=self.close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Modal dialog dismissed!"),
        )

    def close_dlg(self, e):
        self.dlg_modal.open = False
        self.page.update()
        self.mark(self.marked_frame_num, self.dlg_modal.actions[0].value)

    def open_dlg_modal(self, e, frame_num):
        self.marked_frame_num = frame_num
        self.generate_dlg_modal()
        self.page.dialog = self.dlg_modal
        self.dlg_modal.open = True
        self.page.update()


def main(page: ft.Page):
    page.window_width = 650  # window's width is 200 px
    page.window_height = 460  # window's height is 200 px
    page.update()

    page.title = "Video Capture With Marker"
    cap_ctr = CameraCaptureControl()
    marker = Marker(page)

    def record_button_clicked(e):
        recording_style = ft.ButtonStyle(
            color={
                ft.MaterialState.DEFAULT: ft.colors.WHITE,
            },
            bgcolor={"": ft.colors.RED},
        )

        style = ft.ButtonStyle(
            color={
                ft.MaterialState.DEFAULT: ft.colors.WHITE,
            },
            bgcolor={"": ft.colors.BLUE},
        )

        if b1.text == "Record":
            cap_ctr.start_record()

            b1.style = recording_style
            b1.text = "Stop record"
            b1.icon = "stop"
            b1.icon_color = ft.colors.BLACK

            b3.disabled = False

        else:
            cap_ctr.end_record()
            marker_save_path = os.path.join(SAVE_FOLDER_PATH, f"{cap_ctr.now_str}_marker.csv")
            marker.save(path=marker_save_path)

            b1.style = style
            b1.text = "Record"
            b1.icon = "FIBER_MANUAL_RECORD"
            b1.icon_color = ft.colors.RED
            b3.disabled = True

            page.snack_bar = ft.SnackBar(ft.Text(f"Saved video and marker\nsave folder: {os.path.abspath('./record_data/')}"))
            page.snack_bar.open = True
            page.update()

        page.update()

    def button3_clicked(e):
        marker.open_dlg_modal(e, cap_ctr.frame_num)

    b1 = ft.ElevatedButton(
        "Record",
        on_click=record_button_clicked,
        data=0,
        style=ft.ButtonStyle(
            color={
                ft.MaterialState.DEFAULT: ft.colors.WHITE,
            },
            bgcolor={"": ft.colors.BLUE},
        ),
        icon="FIBER_MANUAL_RECORD",
        icon_color=ft.colors.RED,
    )
    b3 = ft.ElevatedButton("Marker", on_click=button3_clicked, data=0, disabled=True, icon="CHECK_CIRCLE")

    row1 = ft.ResponsiveRow(
        spacing=0,
        controls=[
            ft.Container(
                b1,
                padding=5,
                col={"sm": 3},
            ),
            ft.Container(
                b3,
                padding=5,
                col={"sm": 3},
            ),
        ],
    )

    page.add(row1, cap_ctr)


# SAVE_FOLDER_PATH = "./record_data"
# os.makedirs(SAVE_FOLDER_PATH, exist_ok=True)

SAVE_FOLDER_PATH = "./record_data"
SAVE_FOLDER_PATH = os.path.join(os.path.dirname(sys.argv[0]), SAVE_FOLDER_PATH)
os.makedirs(SAVE_FOLDER_PATH, exist_ok=True)

ft.app(target=main)
