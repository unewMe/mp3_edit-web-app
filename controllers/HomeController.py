import sys
import os
import pickle
import webbrowser

from PySide6 import QtCore
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QMenu

from views.HomeView import HomeView
from cores.HomeCore import HomeCore
from views.popups.PopUpMsg import PopUpMsg
from views.tools.url import UrlPopUp
from views.tools.ai import AiPopUp
from views.tools.record import RecordPopUp
from views.popups.selectors import PathSelectorPopUp, PathSelectorWithTypeAndFileName

plots_type_with_values = {"Rythmic": ["Tempogram", "Beats"], "Segmentation": ["Silent segments", "Beat segments"],
                          "Base visualize": ["Waveform", "Spectrogram"]}


class HomeController:
    view: HomeView
    core: HomeCore
    pop_url: UrlPopUp
    pop_ai: AiPopUp
    pop_rec: RecordPopUp

    def __init__(self):
        super().__init__()
        self.view = HomeView(self)
        self.core = HomeCore()
        self.pop_url = UrlPopUp()
        self.pop_ai = AiPopUp()
        self.pop_rec = RecordPopUp()

        # Connect signals

        # Menu bar

        self.view.file_action_export.triggered.connect(lambda ind, id='multiplayer': self.export_audio(id))
        self.view.file_action_save.triggered.connect(self.save_project)
        self.view.file_action_open_recent.triggered.connect(self.open_recent_project)

        self.view.tools_action_url.triggered.connect(self.url_download)
        self.view.tools_action_ai.triggered.connect(self.ai_download)
        self.view.tools_action_recorder.triggered.connect(self.recorder)

        self.view.help_action_about.triggered.connect(lambda: webbrowser.open('https://github.com/unewMe/mp3_edit-app'))

        # Files widget
        self.view.add_file_button.clicked.connect(self.add_file)
        self.view.remove_files_button.clicked.connect(self.remove_file)

        self.view.read_files_list.itemSelectionChanged.connect(self.file_selected)
        self.view.read_files_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.read_files_list.customContextMenuRequested.connect(self.show_context_file_read)

        # Players widget

        self.view.create_player_button.clicked.connect(self.create_player)
        self.view.remove_player_button.clicked.connect(self.remove_player)

        self.view.created_players_list.itemSelectionChanged.connect(self.view.update_player_info)
        self.view.created_players_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.created_players_list.customContextMenuRequested.connect(self.show_context_player)

        # Plots widget

        self.view.generated_plots_list.itemSelectionChanged.connect(self.show_plot)
        self.view.remove_generated_plot_button.clicked.connect(self.remove_plot)

        # Main player widget

        self.view.play_button.clicked.connect(self.play_multiplayer)

        self.playback_timer = QTimer()
        self.playback_timer.setInterval(1000)
        self.playback_timer.timeout.connect(self.update_playing)

        self.view.stop_button.clicked.connect(self.stop_multiplayer)

        self.view.multiplayer_slider.sliderPressed.connect(self.music_slider_clicked)
        self.view.multiplayer_slider.sliderReleased.connect(self.music_slider_changed)

        self.view.main_volume_slider.valueChanged.connect(self.set_main_volume)

        # Player editing frame

        self.view.add_to_player_button.clicked.connect(self.add_file_to_player)
        self.view.remove_from_player_button.clicked.connect(self.remove_file_from_player)

        self.view.audios_in_player_list.itemSelectionChanged.connect(self.update_audio_info)
        self.view.audios_in_player_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.audios_in_player_list.customContextMenuRequested.connect(self.show_context_file_player)

        self.view.queue_up_button.clicked.connect(self.queue_up)
        self.view.queue_down_button.clicked.connect(self.queue_down)

        self.view.audio_volume_slider.sliderReleased.connect(self.set_audio_volume)
        self.view.audio_delay_edit.editingFinished.connect(self.set_audio_delay)

        self.view.add_filter_butoon.clicked.connect(self.add_filter_on_audio)
        self.view.remove_all_filters_button.clicked.connect(self.remove_all_filters_on_audio)
        self.view.remove_all_filters_button.hide()

        self.view.plots_type_combobox.currentIndexChanged.connect(self.update_plots)
        self.view.plots_type_list.itemSelectionChanged.connect(self.plot_selected)
        self.view.generate_plot_button.clicked.connect(self.generate_plot)

        for s_band, slider in self.view.equalizer_sliders.items():
            slider.setProperty('band', s_band)
            slider.valueChanged.connect(lambda ind, band=s_band: self.set_band(band, ind))

    def show(self) -> None:
        """Shows the home view."""

        self.view.show()

    def add_file(self) -> None:
        """Opens a file dialog to select an audio file and adds it to the file list."""

        file_path, _ = QFileDialog.getOpenFileName(self.view, "Open Audio File", "",
                                                   "Audio Files (*.mp3);;All Files (*)")
        if file_path:
            self.core.add_file(file_path)
            self.view.update_file_list(self.core.files)

    def remove_file(self) -> None:
        """Removes the selected file from the file list."""

        file_name = self.view.read_files_list.currentItem().text()
        self.core.remove_file(file_name)
        self.view.update_file_list(self.core.files)

    def file_selected(self) -> None:
        """Updates the audio information in the view."""
        self.view.update_file_selected()

    def create_player(self) -> None:
        """Creates a new player and updates the player list in the view."""

        self.core.create_player()
        self.view.update_player_list(self.core.players)

    def remove_player(self) -> None:
        """Removes the selected player from the player list."""

        player_name = self.view.created_players_list.currentItem().text()
        self.core.remove_player(player_name)
        self.view.update_player_list(self.core.players)
        bands = self.core.get_bands()
        bands_value_reset = {band: 0 for band in bands}
        self.view.update_audio_info(delay=0, volume=60, filters_in=[], filters_out=[],bands=bands_value_reset,plots={})

    def add_file_to_player(self) -> None:
        """Adds the selected file to the selected player."""

        file_name = self.view.read_files_list.currentItem().text()
        player_name = self.view.created_players_list.currentItem().text()
        if self.core.add_file_to_player(file_name, player_name):
            self.view.update_player_audio_list(self.core.players[player_name].play_order)
        else:
            PopUpMsg("Error", "File already added to player.", buttons=QMessageBox.Ok, if_exec=True)

    def remove_file_from_player(self) -> None:
        """Removes the selected file from the selected player."""

        file_name = self.view.audios_in_player_list.currentItem().text()
        player_name = self.view.created_players_list.currentItem().text()
        self.core.remove_from_player(file_name, player_name)
        self.view.update_player_audio_list(self.core.players[player_name].play_order)
        self.update_audio_info()

    def play_multiplayer(self) -> None:
        """Plays all the audio files from all the players."""

        if self.view.play_button.text() == "Pause":
            self.core.multiplayer.pause_all()
            self.playback_timer.stop()
            self.view.play_button.setText("Resume")
        elif self.view.play_button.text() == "Resume":
            self.core.multiplayer.resume_all()
            self.playback_timer.start()
            self.view.play_button.setText("Pause")
        else:
            self.core.combine_audio_files()
            self.view.update_max_timer_and_slider(self.core.get_max_length_in_seconds())
            self.playback_timer.start()
            self.core.play_multiplayer(self.view.main_volume_slider.value() / 100)
            self.view.play_button.setText("Pause")

    def update_playing(self) -> None:
        """Updates the playback time and stops the timer if the playback is finished."""

        if self.core.multiplayer.is_playing:
            self.view.update_timer_and_slider(self.core.get_current_time())
        else:
            self.playback_timer.stop()
            self.view.play_button.setText("Play")
            self.view.update_timer_and_slider((0, 0, 0))
            if not self.check_if_audio():
                self.view.play_button.setEnabled(False)
                self.view.stop_button.setEnabled(False)

    def stop_multiplayer(self) -> None:
        """Stops the playback of all players."""

        self.core.stop_multiplayer()
        self.view.play_button.setText("Play")
        self.playback_timer.stop()
        self.view.update_timer_and_slider((0, 0, 0))
        if not self.check_if_audio():
            self.view.play_button.setEnabled(False)
            self.view.stop_button.setEnabled(False)

    def music_slider_clicked(self) -> None:
        """Pauses the playback when the slider is clicked."""

        self.playback_timer.stop()
        self.core.pause_multiplayer()

    def music_slider_changed(self) -> None:
        """Resumes the playback when the slider is released."""

        # self.core.multiplayer.timer.set_time(self.view.multiplayer_slider.value())
        self.core.multiplayer.set_time(self.view.multiplayer_slider.value())
        self.core.multiplayer.resume_all()
        self.view.play_button.setText("Pause")
        # self.core.multiplayer.timer.start()
        self.playback_timer.start()
        self.view.update_timer_and_slider(self.core.get_current_time())

    def url_download(self) -> None:
        """Opens a popup to download an audio file from a URL."""

        self.pop_url.show()

    def ai_download(self) -> None:
        """Opens a popup to download an audio file from an AI."""

        self.pop_ai.show()

    def check_if_audio(self) -> bool:
        """Checks if any audio is loaded into the player."""

        return self.core.check_if_any_audio_is_loaded_into_player()

    def queue_changed(self) -> None:
        """Updates the play order of the selected player."""

        self.view.created_players_list.currentItem().text()
        self.core.update_player_order(self.view.created_players_list.currentItem().text(),
                                      [self.view.audios_in_player_list.item(i).text() for i in
                                       range(self.view.audios_in_player_list.count())])

    def queue_up(self) -> None:
        """Moves the selected audio up in the play order."""

        item1 = self.view.audios_in_player_list.currentItem().text()
        item2 = self.view.audios_in_player_list.item(self.view.audios_in_player_list.currentRow() - 1).text()
        self.view.audios_in_player_list.item(self.view.audios_in_player_list.currentRow() - 1).setText(item1)
        self.view.audios_in_player_list.currentItem().setText(item2)

        self.view.audios_in_player_list.setCurrentRow(self.view.audios_in_player_list.currentRow() - 1)

        self.queue_changed()

    def queue_down(self) -> None:
        """Moves the selected audio down in the play order."""

        item1 = self.view.audios_in_player_list.currentItem().text()
        item2 = self.view.audios_in_player_list.item(self.view.audios_in_player_list.currentRow() + 1).text()
        self.view.audios_in_player_list.item(self.view.audios_in_player_list.currentRow() + 1).setText(item1)
        self.view.audios_in_player_list.currentItem().setText(item2)

        self.view.audios_in_player_list.setCurrentRow(self.view.audios_in_player_list.currentRow() + 1)

        self.queue_changed()

    def update_audio_info(self) -> None:
        """Updates the audio information in the view."""

        if not self.view.created_players_list.selectedItems():
            return

        if self.view.audios_in_player_list.selectedItems():
            selected_audio = self.view.audios_in_player_list.currentItem().text()
            player_name = self.view.created_players_list.currentItem().text()
            delay, volume = self.core.get_audio_delay_in_player(player_name,
                                                                selected_audio), self.core.get_volume_on_sound_in_player(
                player_name, selected_audio)
            filters_in = self.core.get_filters_from_sound(player_name, selected_audio)
            filters_out = self.core.get_rest_of_filters(filters_in)
            self.view.update_audio_info(delay=delay, volume=volume, filters_in=filters_in, filters_out=filters_out,
                                        plots=plots_type_with_values,
                                        bands=self.core.all_bands_value_from_audio(player_name, selected_audio))
        else:
            self.view.update_audio_info(delay=0, volume=60, filters_in=[], filters_out=[],
                                        plots=plots_type_with_values, bands={})

    def set_audio_volume(self) -> None:
        """Sets the volume of the selected audio in the selected player."""

        selected_audio = self.view.audios_in_player_list.currentItem().text()
        player_name = self.view.created_players_list.currentItem().text()
        volume = self.view.audio_volume_slider.value()
        self.core.set_volume_on_sound(player_name, selected_audio, volume)

    def set_audio_delay(self) -> None:
        """Sets the delay of the selected audio in the selected player."""

        selected_audio = self.view.audios_in_player_list.currentItem().text()
        player_name = self.view.created_players_list.currentItem().text()
        delay = self.view.audio_delay_edit.text()
        try:
            if int(delay) < 0:
                PopUpMsg("Error", "Delay must be a positive int number.", buttons=QMessageBox.Ok, if_exec=True)
                self.view.audio_delay_edit.setText(
                    f"{self.core.get_audio_delay_in_player(player_name, selected_audio)}")
        except ValueError:
            PopUpMsg("Error", "Delay must be a positive int number.", buttons=QMessageBox.Ok, if_exec=True)
            self.view.audio_delay_edit.setText(f"{self.core.get_audio_delay_in_player(player_name, selected_audio)}")
        else:
            self.core.set_audio_delay(player_name, selected_audio, int(delay))

    def add_filter_on_audio(self) -> None:
        """Adds a filter on the selected audio in the selected player."""

        selected_audio = self.view.audios_in_player_list.currentItem().text()
        player_name = self.view.created_players_list.currentItem().text()
        self.core.add_filter_on_audio(player_name, selected_audio, self.view.filter_type_combobox.currentText())
        self.update_audio_info()

    def remove_all_filters_on_audio(self) -> None:
        """Removes all filters on the selected audio in the selected player."""

        selected_audio = self.view.audios_in_player_list.currentItem().text()
        player_name = self.view.created_players_list.currentItem().text()
        self.core.remove_all_filters_on_audio(player_name, selected_audio)
        self.update_audio_info()

    def update_plots(self) -> None:
        """Updates the plots in the audio edit."""
        if any(item.isSelected() for item in self.view.audios_in_player_list.selectedItems()):
            self.view.update_plot_type(plots_type_with_values)

    def plot_selected(self) -> None:
        """Updates the plot type in the audio edit."""
        if self.view.plots_type_list.selectedItems():
            self.view.generate_plot_button.setEnabled(True)
        else:
            self.view.generate_plot_button.setEnabled(False)

    def remove_plot(self) -> None:
        """Removes the selected plot from the plot list in the view."""

        plot_name = self.view.generated_plots_list.currentItem().text()
        self.core.remove_plot(plot_name)
        self.view.update_plots(self.core.plots)

    def generate_plot(self) -> None:
        """Generates a plot and updates the plot list in the view."""

        player_name = self.view.created_players_list.currentItem().text()
        selected_audio = self.view.audios_in_player_list.currentItem().text()
        type = self.view.plots_type_combobox.currentText()
        plots = [plot.text() for plot in self.view.plots_type_list.selectedItems()]
        path_selector = PathSelectorPopUp()
        path_selector.exec_()
        path = path_selector.directory
        if path and os.path.isdir(path):
            self.core.generate_plot(player_name, selected_audio, path, type, plots)
            PopUpMsg("Success", "Plot generated successfully.", buttons=QMessageBox.Ok, if_exec=True)
            self.view.update_plots(self.core.plots)

    def show_plot(self) -> None:
        """Shows the selected plot in the view."""
        if self.view.generated_plots_list.selectedItems():
            plot_name = self.view.generated_plots_list.currentItem().text()
            self.view.show_plot(self.core.plots[plot_name])
        else:
            self.view.show_plot(None)

    def set_band(self, band, ind):
        """Sets the band of the equalizer in the selected audio."""

        if self.view.audios_in_player_list.selectedItems():
            self.view.audio_volume_slider.setValue(60)
            selected_audio = self.view.audios_in_player_list.currentItem().text()
            player_name = self.view.created_players_list.currentItem().text()
            value = self.view.equalizer_sliders[band].value()
            self.core.set_band_on_audio(player_name, selected_audio, band, value)

    def recorder(self):
        """Opens a popup to record an audio file."""

        self.pop_rec.show()

    def export_audio(self, id: str) -> None:
        """Exports the selected audio file."""

        path_type_filename = PathSelectorWithTypeAndFileName()
        if not path_type_filename.is_rejected:
            path_type_filename.exec()
            path, filename, type = path_type_filename.path, path_type_filename.file_name, path_type_filename.file_type
            if path and filename and type:
                match id:
                    case 'multiplayer':
                        self.core.export(self.core.multiplayer, path + '/' + filename + '.' + type, type)
                    case 'player':
                        player_name = self.view.created_players_list.currentItem().text()
                        self.core.export(self.core.players[player_name], path + '/' + filename + '.' + type, type)
                    case 'file_read':
                        file_name = self.view.read_files_list.currentItem().text()
                        self.core.export(self.core.files[file_name], path + '/' + filename + '.' + type, type)
                    case 'file_player':
                        player_name = self.view.created_players_list.currentItem().text()
                        audio_name = self.view.audios_in_player_list.currentItem().text()
                        self.core.export(self.core.players[player_name].sound_files[audio_name],
                                         path + '/' + filename + '.' + type, type)

    def show_context_player(self, pos) -> None:
        """Shows the context menu for the player list."""

        if not self.view.created_players_list.currentItem():
            return

        menu = QMenu()
        export_action = menu.addAction("Export")
        export_action.triggered.connect(lambda ind, id='player': self.export_audio(id))
        menu.addAction(export_action)

        menu.exec_(self.view.created_players_list.mapToGlobal(pos))

    def show_context_file_read(self, pos) -> None:
        """Shows the context menu for the file list."""

        if not self.view.read_files_list.currentItem():
            return

        menu = QMenu()
        export_action = menu.addAction("Export")
        export_action.triggered.connect(lambda ind, id='file_read': self.export_audio(id))
        menu.addAction(export_action)

        menu.exec_(self.view.read_files_list.mapToGlobal(pos))

    def show_context_file_player(self, pos) -> None:
        """Shows the context menu for the audio list in the player."""

        if not self.view.audios_in_player_list.currentItem():
            return

        menu = QMenu()
        export_action = menu.addAction("Export")
        export_action.triggered.connect(lambda ind, id='file_player': self.export_audio(id))
        menu.addAction(export_action)

        menu.exec_(self.view.audios_in_player_list.mapToGlobal(pos))

    def set_main_volume(self) -> None:
        """Sets the main volume of the player."""
        volume = self.view.main_volume_slider.value()
        self.core.set_main_volume(volume / 100)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['view']
        del state['pop_url']
        del state['pop_ai']
        del state['pop_rec']
        del state['playback_timer']
        return state

    def save_project(self) -> None:
        """Saves the current core of project using pickle."""
        with open('secret.pkl', 'wb') as f:
            pickle.dump(self, f)
        PopUpMsg("Success", "Project saved successfully.", buttons=QMessageBox.Ok, if_exec=True)

    def open_recent_project(self) -> None:
        """Opens the most recent project."""
        if os.path.exists('secret.pkl'):
            with open('secret.pkl', 'rb') as f:
                controller = pickle.load(f)

            self.core = controller.core

            self.view.update_file_list(self.core.files)
            self.view.update_player_list(self.core.players)
            self.view.update_plots(self.core.plots)
            if self.check_if_audio():
                self.view.play_button.setEnabled(True)
                self.view.stop_button.setEnabled(True)
        else:
            PopUpMsg("Error", "No recent project found.", buttons=QMessageBox.Ok, if_exec=True)
