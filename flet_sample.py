import base64
import threading
import os
import time
import csv
import cv2
import flet as ft


def duplicate_rename(file_path):
    if os.path.exists(file_path):
        name, ext = os.path.splitext(file_path)
        i = 1
        while True:
            # 数値を3桁などにしたい場合は({:0=3})とする
            new_name = f"{name}({i:0=3}){ext}"
            if not os.path.exists(new_name):
                return new_name
            i += 1
    else:
        return file_path


class CameraCaptureControl(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.capture = cv2.VideoCapture(0)
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = 29.97
        self.record = None
        self.writer = None
        self.frame_num = 0

    def generate_writer(self):

        # VideoWriter を作成する。
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        return cv2.VideoWriter(duplicate_rename("output.mp4"), fourcc, self.fps, (self.width, self.height))

    def did_mount(self):
        self.running = True
        self.thread = threading.Thread(target=self.update_frame, args=(), daemon=True)
        self.thread.start()

    def will_unmount(self):
        self.running = False

    def start_record(self):
        self.record = True
    
    def end_record(self):
        self.record = False

    def update_frame(self):
        while self.capture.isOpened() and self.running:
            # TODO retvalのチェックとハンドリングを実装
            retval, self.raw_frame = self.capture.read()
            self.frame = cv2.resize(self.raw_frame, (640, 360))
            retval, self.frame = cv2.imencode(".jpg", self.frame)
            data = base64.b64encode(self.frame)
            self.image_control.src_base64 = data.decode()
            self.update()

            if self.record is not None:
                if self.writer is None:
                    self.writer = self.generate_writer()

                if self.record:
                    self.writer.write(self.raw_frame)  # フレームを書き込む。
                    self.frame_num += 1
                
                else:
                    self.writer.release()

                    self.record = None
                    self.writer = None

            # sleep(self.latency)

    def build(self):
        self.image_control = ft.Image(
            width=640,
            # width=self.capture.get(cv2.CAP_PROP_FRAME_WIDTH),
            height=360,
            # height=self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT),
            fit=ft.ImageFit.FIT_WIDTH,
        )
        return self.image_control

class Marker():
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
    page.window_width = 650        # window's width is 200 px
    page.window_height = 460       # window's height is 200 px
    page.update()


    page.title = "Elevated button with 'click' event"
    cap_ctr = CameraCaptureControl()
    marker = Marker(page)


    def button1_clicked(e):
        cap_ctr.start_record()

    def button2_clicked(e):
        cap_ctr.end_record()
        marker.save()

    def button3_clicked(e):
        marker.open_dlg_modal(e, cap_ctr.frame_num)

    b1 = ft.ElevatedButton("Start record", on_click=button1_clicked, data=0)
    b2 = ft.ElevatedButton("End record", on_click=button2_clicked, data=0)
    b3 = ft.ElevatedButton("Marker", on_click=button3_clicked, data=0)

    row1 = ft.ResponsiveRow(spacing=0, controls=[ft.Container(
                    b1,
                    padding=5,
                    col={"sm": 3},
                ),ft.Container(
                    b2,
                    padding=5,
                    col={"sm": 3},
                ),ft.Container(
                    b3,
                    padding=5,
                    col={"sm": 3},
                )])
    # row2 = ft.ResponsiveRow(spacing=0, controls=[cap_ctr])

    page.add(row1, cap_ctr)

ft.app(target=main)

