import os
import re
import sys
import shutil
import subprocess
import logging
from send2trash import send2trash
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

NO_REEL = "No reel available"
NO_SHOT = "No shot available"

# Project wise version pattern
VERSION_PATTERN={
    "default":3,
}



class ProjectBrowser(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.PROJECT_LOCATIONS = config.get("PROJECT_LOCATIONS", {})
        self.SOFTWARES = config.get("SOFTWARES", {})
        self.TASKS_2D = config.get("TASKS_2D", [])
        self.TASKS_3D = config.get("TASKS_3D", [])
        self.LOGO_PATH = config.get("LOGO_PATH", "./logo.png")

        self.setWindowTitle("Datalok | 1.0.8")
        self.setGeometry(100, 100, 600, 600)
        self.layout = QVBoxLayout(self)

        self.setup_logo()
        self.setup_layouts()
        self.setup_combos()
        self.setup_file_list()
        self.populate_projects()
        self.center_window()

    def setup_logo(self):
        self.logo_label = QLabel(self)
        pixmap = QPixmap(self.LOGO_PATH).scaled(100, 100, Qt.KeepAspectRatio)
        self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.logo_label)

    def setup_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.buttons_layout = QVBoxLayout()
        self.data_layout = QVBoxLayout()
        self.layout.addLayout(self.main_layout)
        self.main_layout.addLayout(self.buttons_layout, 2)
        self.main_layout.addLayout(self.data_layout, 3)

    def setup_combos(self):
        self.project_combo = self.create_combobox("Project", self.on_project_selected)
        self.reel_combo = self.create_combobox("Reel", self.on_reel_selected)
        self.shot_combo = self.create_combobox("Shot", self.on_shot_selected)
        self.dept_type_combo = self.create_combobox(
            "Department", self.on_dept_type_selected
        )
        self.task_combo = self.create_combobox("Task", self.on_task_selected)
        self.software_combo = self.create_combobox(
            "Software", self.on_software_selected
        )

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(
            ["Sort: Z-A", "Sort: A-Z", "Sort: Newest", "Sort: Oldest"]
        )
        self.sort_combo.currentIndexChanged.connect(self.on_software_selected)
        self.data_layout.addWidget(self.sort_combo)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            ["All Files", "Main Files", "My Files", "All Users Files"]
        )
        self.filter_combo.currentIndexChanged.connect(self.on_software_selected)
        self.data_layout.addWidget(self.filter_combo)

    def setup_file_list(self):
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.handle_file_action)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)
        self.data_layout.addWidget(self.file_list)

    def create_combobox(self, label, callback):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.currentIndexChanged.connect(callback)
        layout.addWidget(combo)
        self.buttons_layout.addLayout(layout)
        return combo

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2
        )

    def populate_projects(self):
        self.project_combo.clear()
        self.project_combo.addItem("Select Project", None)
        for root, render in self.PROJECT_LOCATIONS.items():
            if not os.path.exists(root):
                continue
            drive = os.path.splitdrive(root)[0]
            for p in os.listdir(root):
                full_path = os.path.join(root, p)
                if os.path.isdir(full_path):
                    label = f"{drive}-{p}"
                    self.project_combo.addItem(label, (p, root, render))

    def on_project_selected(self):
        self.clear_combos(1)
        project_info = self.project_combo.currentData()
        if not project_info:
            return
        project, root_path, _ = project_info
        scan_path = os.path.join(root_path, project, "SCAN")
        reels = sorted(os.listdir(scan_path)) if os.path.exists(scan_path) else []
        if reels:
            self.reel_combo.addItems(reels)
        else:
            self.reel_combo.addItem(NO_REEL)

    def on_reel_selected(self):
        self.clear_combos(2)
        project_info = self.project_combo.currentData()
        if not project_info:
            return
        project, root_path, _ = project_info
        reel = self.reel_combo.currentText()
        if reel == NO_REEL:
            self.shot_combo.addItem(NO_SHOT)
            return

        shot_path = os.path.join(root_path, project, "SCAN", reel)
        shots = sorted(os.listdir(shot_path)) if os.path.exists(shot_path) else []
        if shots:
            self.shot_combo.addItems(shots)
        else:
            self.shot_combo.addItem(NO_SHOT)

    def on_shot_selected(self):
        self.clear_combos(3)
        if self.shot_combo.currentText() not in [NO_SHOT, ""]:
            self.dept_type_combo.addItems(["2d", "3d"])

    def on_dept_type_selected(self):
        self.clear_combos(4)
        dept = self.dept_type_combo.currentText()
        if dept == "2d":
            self.task_combo.addItems(self.TASKS_2D)
        elif dept == "3d":
            self.task_combo.addItems(self.TASKS_3D)

    def on_task_selected(self):
        self.clear_combos(5)
        self.software_combo.addItems(self.SOFTWARES.keys())

    def filter_file_type(self, full_path, extension):
        if os.path.isfile(full_path) and full_path.endswith(extension):
            return True
        if full_path.endswith(extension) and os.path.isfile(
            os.path.join(full_path, "project.sfx")
        ):
            return True
        return False

    # def on_software_selected(self):
    #     self.file_list.clear()
    #     software = self.software_combo.currentText()
    #     ext = self.SOFTWARES.get(software, {}).get("extension", "txt")
    #     # print(software,ext)
    #     folder = self.get_workfile_path()
    #     if not folder:
    #         return
    #     os.makedirs(folder, exist_ok=True)

    #     files = [
    #         f for f in os.listdir(folder) if (os.path.isfile(os.path.join(folder, f)) or  f.endswith(ext))
    #     ]
    #     sort_mode = self.sort_combo.currentText()
    #     if sort_mode == "Sort: A-Z":
    #         files.sort()
    #     elif sort_mode == "Sort: Z-A":
    #         files.sort(reverse=True)
    #     elif sort_mode == "Sort: Newest":
    #         files.sort(
    #             key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True
    #         )
    #     elif sort_mode == "Sort: Oldest":
    #         files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)))

    #     for f in files:
    #         if not f.endswith(ext):
    #             continue
    #         item = QListWidgetItem(f)
    #         item.setData(
    #             Qt.UserRole, {"filepath": os.path.join(folder, f), "software": software}
    #         )
    #         self.file_list.addItem(item)

    #     # Add "Create New" item
    #     create_item = QListWidgetItem("🆕 Create New File")
    #     create_item.setData(
    #         Qt.UserRole, {"create_new": True, "folder": folder, "software": software}
    #     )
    #     self.file_list.addItem(create_item)

    def on_software_selected(self):
        self.file_list.clear()
        paths = self.get_path()
        if not paths:
            return

        work_file_path = paths.get("work_file_path")
        native_path = paths.get("native_path")
        raw_data = paths.get("raw_data")
        os.makedirs(work_file_path, exist_ok=True)

        software = self.software_combo.currentText()
        extension = self.get_software_extension(software)
        username = self.get_user()
        filter_mode = self.filter_combo.currentText()
        print(filter_mode)

        # 🧹 Apply file filters
        filtered_files = []
        # for filename, full_path in all_files:
        if filter_mode == "Main Files":
            for f in os.listdir(work_file_path):
                full_path = os.path.join(work_file_path, f)
                temp_full_path = full_path
                if self.filter_file_type(temp_full_path, extension):
                    filtered_files.append((f, temp_full_path))
        elif filter_mode == "My Files":
            artist_data_path = os.path.join(work_file_path, "artist_data")
            if os.path.exists(artist_data_path):
                for user in os.listdir(artist_data_path):
                    user_folder = os.path.join(artist_data_path, user)
                    if os.path.isdir(user_folder) and user == username:
                        for f in os.listdir(user_folder):
                            full_path = os.path.join(user_folder, f)
                            temp_full_path = full_path
                            if self.filter_file_type(temp_full_path, extension):
                                filtered_files.append((f, temp_full_path))
        elif filter_mode == "All User Files":
            artist_data_path = os.path.join(work_file_path, "artist_data")
            if os.path.exists(artist_data_path):
                for user in os.listdir(artist_data_path):
                    user_folder = os.path.join(artist_data_path, user)
                    if os.path.isdir(user_folder):
                        for f in os.listdir(user_folder):
                            full_path = os.path.join(user_folder, f)
                            temp_full_path = full_path
                            if self.filter_file_type(temp_full_path, extension):
                                filtered_files.append((f, temp_full_path))
        else:  # All Files
            # 🔍 Gather main work files
            for f in os.listdir(work_file_path):
                full_path = os.path.join(work_file_path, f)
                temp_full_path = full_path
                if self.filter_file_type(temp_full_path, extension):
                    filtered_files.append((f, temp_full_path))

            # 🔍 Gather files inside artist_data subfolders
            artist_data_path = os.path.join(work_file_path, "artist_data")
            if os.path.exists(artist_data_path):
                for user in os.listdir(artist_data_path):
                    user_folder = os.path.join(artist_data_path, user)
                    if os.path.isdir(user_folder):
                        for f in os.listdir(user_folder):
                            full_path = os.path.join(user_folder, f)
                            temp_full_path = full_path
                            if not f.endswith(".sfx"):
                                temp_full_path = os.path.join(user_folder, f)
                                os.rename(full_path,temp_full_path)
                            if self.filter_file_type(temp_full_path, extension):
                                filtered_files.append((f, temp_full_path))

        # 🗂 Sorting
        # print(filtered_files)
        sort_mode = self.filter_combo.currentText()
        if sort_mode == "Sort: A-Z":
            filtered_files.sort()
        elif sort_mode == "Sort: Z-A":
            filtered_files.sort(reverse=True)
        elif sort_mode == "Sort: Newest":
            filtered_files.sort(key=lambda x: os.path.getmtime(x[1]), reverse=True)
        elif sort_mode == "Sort: Oldest":
            filtered_files.sort(key=lambda x: os.path.getmtime(x[1]))

        # 🧾 Display files
        for filename, full_path in filtered_files:
            item = QListWidgetItem(filename)
            item.setData(
                Qt.UserRole,
                {
                    "filepath": full_path,
                    "plate": native_path,
                    "software": software,
                    "raw_data":raw_data
                },
            )
            self.file_list.addItem(item)

        # ➕ Add "Create New File" option
        create_item = QListWidgetItem("\U0001f195 Create New File")
        create_item.setData(
            Qt.UserRole,
            {
                "create_new": True,
                "folder": work_file_path,
                "plate": native_path,
                "software": software,
            },
        )
        self.file_list.addItem(create_item)

    def get_software_extension(self, software):
        extension = self.SOFTWARES.get(software, {}).get("extension", "txt")
        return extension

    def get_path(self):
        project_info = self.project_combo.currentData()
        if not project_info:
            return None
        project, root_path, _ = project_info
        reel = self.reel_combo.currentText()
        shot = self.shot_combo.currentText()
        dept_type = self.dept_type_combo.currentText()
        task = self.task_combo.currentText()
        software = self.software_combo.currentText()

        extension = self.get_software_extension(software)

        if any(x in ["", NO_REEL, NO_SHOT] for x in [project, reel, shot]):
            return None

        new_path = os.path.join(
            root_path, project, "workfile", reel, shot, dept_type, task, extension
        )
        return {"native_path": root_path, "work_file_path": new_path,"raw_data":""}

    def clear_combos(self, start):
        combos = [
            self.reel_combo,
            self.shot_combo,
            self.dept_type_combo,
            self.task_combo,
            self.software_combo,
        ]
        for combo in combos[start - 1 :]:
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)
        self.file_list.clear()

    def handle_file_action(self, item):
        data = item.data(Qt.UserRole)
        if data.get("create_new"):
            self.create_new_file(data["folder"], data["software"])
        else:
            self.open_file(data["filepath"], data["software"])

    def show_context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if item:
            menu = QMenu()
            data = item.data(Qt.UserRole)
            if not data.get("create_new"):
                menu.addAction(
                    "Open", lambda: self.open_file(data["filepath"], data["software"])
                )
                menu.addAction("Rename", lambda: self.rename_file(item))
                menu.addAction("Delete", lambda: self.delete_file(item))
                menu.addAction(
                    "Version Up",
                    lambda: self.version_up(data["filepath"], data["software"]),
                )
                menu.addAction(
                    "Save as User",
                    lambda: self.save_as_user(data["filepath"], data["software"]),
                )
                menu.addAction(
                    "Save as Main",
                    lambda: self.save_as_main(data["filepath"], data["software"]),
                )
                menu.addAction("Explore", lambda: self.explore_file(data["filepath"]))
            menu.exec(self.file_list.mapToGlobal(pos))

    def create_new_file(self, folder, software):
        project_info = self.project_combo.currentData()
        project, root_path, _ = project_info
        shot = self.shot_combo.currentText()
        task = self.task_combo.currentText()
        ext = self.get_software_extension(software)
        template_dir = self.config.get("TEMPLATE_PATH", "./_templates")

        # Try project-specific template first, then fallback to default
        template_path = os.path.join(template_dir, project, task, f"{software}.{ext}")
        template_source = "Project Template"
        if not os.path.exists(template_path):
            template_path = os.path.join(
                template_dir, "default", task, f"{software}.{ext}"
            )
            template_source = "Default Template"
        # print(template_path)

        base_name = f"{shot}_{task}_v"
        version = 1
        while True:
            new_filename = f"{base_name}{version:03d}.{ext}"
            new_filepath = os.path.join(folder, new_filename)
            if not os.path.exists(new_filepath):
                break
            version += 1

        try:
            if software.lower() in ["silhouette", "silhouettefx", "silhouetteboris"]:
                os.makedirs(new_filepath, exist_ok=True)
                silhouette_extension = f"project.{ext}"
                silhouette_target_file = os.path.join(new_filepath, silhouette_extension)
                silhouette_template_path = os.path.join(
                    template_path, silhouette_extension
                )
                if os.path.exists(silhouette_template_path):
                    shutil.copy(silhouette_template_path, silhouette_target_file)
                    QMessageBox.information(
                        self, "File Created from template", f"Created file: {new_filename}"
                    )
                else:
                    with open(silhouette_target_file, "w") as silhouette_file:
                        silhouette_file.write('<Project version="2024.5">\n</Project>')
                        silhouette_file.close()
                    QMessageBox.information(
                        self, "Empty File Created", f"Created file: {new_filename}"
                    )
            else:
                if os.path.exists(template_path):
                    shutil.copy(template_path, new_filepath)
                    QMessageBox.information(
                        self,
                        "File Created",
                        f"Created from {template_source}:\n{new_filename}",
                    )
                else:
                    open(new_filepath, "w").close()
                    QMessageBox.information(
                        self, "File Created", f"Empty file created:\n{new_filename}"
                    )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create file:\n{e}")
        self.on_software_selected()

    def open_file(self, filepath, software):
        exe = self.SOFTWARES.get(software, {}).get("path")
        if not exe or not os.path.exists(exe):
            QMessageBox.warning(self, "Error", f"Executable for {software} not found.")
            return

        project_info = self.project_combo.currentData()
        if not project_info:
            return
        project, root_path, render_path = project_info
        reel = self.reel_combo.currentText()
        shot = self.shot_combo.currentText()
        dept = self.dept_type_combo.currentText()
        task = self.task_combo.currentText()

        env = os.environ.copy()
        env.update(
            {
                "ROOT_PATH": root_path,
                "RENDER_PATH": render_path,
                "PROJECT": project,
                "REEL": reel,
                "SHOT": shot,
                "DEPARTMENT": dept,
                "TASK": task,
                "SOFTWARE": software,
            }
        )

        try:
            logging.info(f"Launching {software} with: {filepath}")
            if "nukex" in software.lower():
                subprocess.Popen([exe, "--nukex", filepath], env=env)
            else:
                subprocess.Popen([exe, filepath], env=env)
        except Exception as e:
            logging.error("Failed to launch software: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")

    def explore_file(self, filepath):
        folder = os.path.dirname(filepath)

        if os.path.exists(folder):
            folder = folder.replace("/", "\\")
            subprocess.Popen(f'explorer "{folder}"')
        else:
            QMessageBox.warning(self, "Error", "Folder does not exist.")

    def rename_file(self, item):
        old_path = item.data(Qt.UserRole)["filepath"]
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(
            self, "Rename File", "Enter new file name:", text=old_name
        )
        if ok and new_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                item.setText(new_name)
                item.setData(
                    Qt.UserRole,
                    {
                        "filepath": new_path,
                        "software": item.data(Qt.UserRole)["software"],
                    },
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Rename failed:\n{e}")

    def delete_file(self, item):
        path = item.data(Qt.UserRole)["filepath"]
        print(path)
        confirm = QMessageBox.question(
            self,
            "Delete File",
            f"Delete {os.path.basename(path)}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                # if os.path.isdir(path):
                #     shutil.rmtree(path)
                #     self.file_list.takeItem(self.file_list.row(item))
                # elif os.path.exists(path):
                #         os.remove(path)
                #         self.file_list.takeItem(self.file_list.row(item))
                # else:
                #      QMessageBox.warning(self, "Error", "File not found.")
                path = path.replace("/", "\\")
                send2trash(path)
                self.file_list.takeItem(self.file_list.row(item))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")

    # def version_up(self, filepath, software):
    #     dirname, filename = os.path.split(filepath)
    #     name, ext = os.path.splitext(filename)
    #     match = re.match(r"(.+)_v(\d{3})", name)
    #     if not match:
    #         QMessageBox.warning(self, "Error", "Filename missing version (_v###).")
    #         return

    #     username = self.get_user()
    #     # base = name.split((f"_{username}_v")[0] + f"_{username}") if f"_{username}_v" in name else name.split("_v")[0]
    #     if f"_{username}_v" in name:
    #         base = name.split(f"_{username}_v")[0] + f"_{username}"
    #     else:
    #         base = name.split("_v")[0]
    #     self._save_version(filepath, dirname, base, ext, software)

    # def save_as_user(self, filepath, software):
    #     shot = self.shot_combo.currentText()
    #     task = self.task_combo.currentText()
    #     version = self.extract_version(filepath)
    #     user = self.get_user()
    #     base = f"{shot}_{task}_v{version:03}_{user}"
    #     dirname, ext = os.path.dirname(filepath), os.path.splitext(filepath)[1]
    #     self._save_version(filepath, dirname, base, ext, software)

    # def save_as_main(self, filepath, software):
    #     name, ext = os.path.splitext(os.path.basename(filepath))
    #     match = re.match(r"(.+?)_v(\d{3})(?:_[a-zA-Z0-9]+_v\d{3})?$", name)
    #     if not match:
    #         QMessageBox.warning(self, "Error", "Invalid format for 'Save as Main'.")
    #         return
    #     base = match.group(1)
    #     dirname = os.path.dirname(filepath)
    #     self._save_version(filepath, dirname, base, ext, software)

    def version_up(self, filepath, software):
        dirname, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        version_digit = VERSION_PATTERN.get(self.project_combo.currentText(),3)
        match = re.match(rf"(.+)_v(\d{{{version_digit}}})", name)
        print(version_digit,self.project_combo.currentText())
        if not match:
            QMessageBox.warning(self, "Error", "Filename does not contain _v###.")
            return
        prefix = match.group(1)
        version = int(match.group(2)) + 1
        while True:
            new_name = f"{prefix}_v{version:0{version_digit}d}{ext}"
            new_path = os.path.join(dirname, new_name)

            if software.lower() in ["silhouette", "silhouettefx", "silhouetteboris"]:
                os.makedirs(new_path, exist_ok=True)
                silhouette_extension = f"project{ext}"
                new_silhouette_source_path = os.path.join(
                    filepath, silhouette_extension
                )
                new_silhouette_dest_path = os.path.join(new_path, silhouette_extension)
                if not os.path.exists(new_silhouette_dest_path):
                    shutil.copy(new_silhouette_source_path, new_silhouette_dest_path)
                    QMessageBox.information(self, "Version Up", f"Saved: {new_name}")
                    self.on_software_selected()
                    break
            else:
                if not os.path.exists(new_path):
                    shutil.copy(filepath, new_path)
                    QMessageBox.information(self, "Version Up", f"Saved: {new_name}")
                    self.on_software_selected()
                    break
            version += 1


    def save_as_user(self, filepath, software):
        shot = self.shot_combo.currentText()
        task = self.task_combo.currentText()
        version_number = self.extract_version(task, os.path.basename(filepath))
        username = self.get_user()
        ext = os.path.splitext(filepath)[1]
        folder = os.path.dirname(filepath)

        # Save inside local artist_data folder within the same working directory
        artist_data_pos = folder.find("artist_data")
        if artist_data_pos != -1:
            folder = folder[:artist_data_pos]
        artist_folder = os.path.join(folder, "artist_data", username)
        os.makedirs(artist_folder, exist_ok=True)

        user_version = 1
        version_digit = VERSION_PATTERN.get(self.project_combo.currentText(),3)
        while True:
            new_filename = (
                f"{shot}_{task}_v{version_number:0{version_digit}d}_{username}_v{user_version:0{version_digit}d}{ext}"
            )
            new_path = os.path.join(artist_folder, new_filename)
            if software.lower() in ["silhouette", "silhouettefx", "silhouetteboris"]:
                os.makedirs(new_path, exist_ok=True)
                silhouette_extension = f"project{ext}"
                new_silhouette_source_path = os.path.join(
                    filepath, silhouette_extension
                )
                new_silhouette_dest_path = os.path.join(new_path, silhouette_extension)
                if not os.path.exists(new_silhouette_dest_path):
                    shutil.copy(new_silhouette_source_path, new_silhouette_dest_path)
                    QMessageBox.information(
                        self, "Saved as User", f"Saved as: {new_filename}"
                    )
                    self.on_software_selected()
                    break
            else:
                if not os.path.exists(new_path):
                    shutil.copy(filepath, new_path)
                    QMessageBox.information(
                        self, "Saved as User", f"Saved as: {new_filename}"
                    )
                    self.on_software_selected()
                    break
            user_version += 1



    def save_as_main(self, filepath, software):
        shot = self.shot_combo.currentText()
        task = self.task_combo.currentText()
        dirname, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        version_digit = VERSION_PATTERN.get(self.project_combo.currentText(),3)
        match = re.match(rf"(.+?)_v(\d{{{version_digit}}})(?:_[a-zA-Z0-9]+_v\d{{{version_digit}}})?$", name)
        if not match:
            QMessageBox.warning(
                self, "Error", "Invalid filename format for Save as Main."
            )
            return
        base = match.group(1)

        # 👇 Strip artist_data from path if present
        artist_data_pos = dirname.find("artist_data")
        if artist_data_pos != -1:
            dirname = dirname[:artist_data_pos]

        version = 1
        while True:
            new_name = f"{shot}_{task}_v{version:0{version_digit}d}{ext}"
            new_path = os.path.join(dirname, new_name)
            if software.lower() in ["silhouette", "silhouettefx", "silhouetteboris"]:
                os.makedirs(new_path, exist_ok=True)
                silhouette_extension = f"project{ext}"
                new_silhouette_source_path = os.path.join(
                    filepath, silhouette_extension
                )
                new_silhouette_dest_path = os.path.join(new_path, silhouette_extension)
                if not os.path.exists(new_silhouette_dest_path):
                    shutil.copy(new_silhouette_source_path, new_silhouette_dest_path)
                    QMessageBox.information(
                        self, "Saved as Main", f"Saved as: {new_name}"
                    )
                    self.on_software_selected()
                    break
            else:
                if not os.path.exists(new_path):
                    shutil.copy(filepath, new_path)
                    QMessageBox.information(
                        self, "Saved as Main", f"Saved as: {new_name}"
                    )
                    self.on_software_selected()
                    break
            version += 1

    def _save_version(self, filepath, dirname, base, ext, software):
        version = 1
        while True:
            filename = f"{base}_v{version:03}{ext}"
            target = os.path.join(dirname, filename)
            if software.lower() in ["silhouette", "silhouettefx", "silhouetteboris"]:
                os.makedirs(target, exist_ok=True)
                silhouette_extension = f"project{ext}"
                new_silhouette_source_path = os.path.join(
                    filepath, silhouette_extension
                )
                new_silhouette_dest_path = os.path.join(target, silhouette_extension)
                if not os.path.exists(new_silhouette_dest_path):
                    shutil.copy(new_silhouette_source_path, new_silhouette_dest_path)
                    QMessageBox.information(self, "Version Up", f"Saved: {filename}")
                    self.on_software_selected()
                    return
            else:
                if not os.path.exists(target):
                    try:
                        shutil.copy(filepath, target)
                        QMessageBox.information(self, "File Saved", f"Saved as {filename}")
                        self.on_software_selected()
                        return
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
                        return
            version += 1

    # def extract_version(self, filename):
    #     name = os.path.basename(filename)
    #     match = re.search(r"_v(\d{3})", name)
    #     return int(match.group(1)) if match else 1

    def extract_version(self, task, filename):
        name = filename.split(task)[-1]
        version_digit = VERSION_PATTERN.get(self.project_combo.currentText(),3)
        match = re.search(rf"_v(\d{{{version_digit}}})", name)
        return int(match.group(1)) if match else 0

    def get_user(self):
        return re.sub(r"\W+", "", os.environ.get("USERNAME", "user123")).lower()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectBrowser(config={})
    window.show()
    sys.exit(app.exec())
