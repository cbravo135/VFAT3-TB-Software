import Tkinter, tkFileDialog, Tkconstants
import time
import os
import ttk
from Tkinter import *
from tti_serial_interface import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class CurrentMonitorInterface:
    def __init__(self, master):
        self.master = master
        self.master.title("Current monitor")
        self.master.minsize(width=340, height=200)

        self.PSU_interface = TtiSerialInterface()
        self.mode = 0
        self.ch1_current = 0
        self.ch2_current = 0
        self.ch1_current_limit = 0.1
        self.ch2_current_limit = 0.1
        self.ch_current_limit_reached = 0
        self.ch_output_state = 0
        self.ch1_history = [0]*200
        self.ch2_history = [0]*200
        self.device0_label = Label(self.master, text="Connected to:")
        self.device0_label.grid(column=1, row=1, sticky='w', columnspan=6)
        self.device_label = Label(self.master, text=self.PSU_interface.device_ID)
        self.device_label.grid(column=1, row=2, sticky='w', columnspan=6)
        self.data_folder = "/home"
        self.save_data = 0
        self.initialize_plot()
        # CH1
        self.ch1_current_label0 = Label(self.master, text="Current 1:")
        self.ch1_current_label0.grid(column=1, row=3, sticky='e')

        self.ch1_current_entry = Entry(self.master, width=6)
        self.ch1_current_entry.grid(column=2, row=3, sticky='e')
        self.ch1_current_entry.insert(0, self.ch1_current)

        self.ch1_current_label = Label(self.master, text="A")
        self.ch1_current_label.grid(column=3, row=3, sticky='w')

        self.ch1_state_label = Label(self.master, text="Off")
        self.ch1_state_label.grid(column=4, row=3, sticky='w')

        # CH2
        self.ch2_current_label0 = Label(self.master, text="Current 2:")
        self.ch2_current_label0.grid(column=1, row=4, sticky='e')

        self.ch2_current_entry = Entry(self.master, width=6)
        self.ch2_current_entry.grid(column=2, row=4, sticky='e')
        self.ch2_current_entry.insert(0, self.ch2_current)

        self.ch2_current_label = Label(self.master, text="A")
        self.ch2_current_label.grid(column=3, row=4, sticky='w')

        self.ch2_state_label = Label(self.master, text="Off")
        self.ch2_state_label.grid(column=4, row=4, sticky='w')

        self.start_button = Button(self.master, text="Start", command=lambda: self.change_mode("start"))
        self.start_button.grid(column=1, row=5, sticky='e')
        self.stop_button = Button(self.master, text="Stop", command=lambda: self.change_mode("stop"))
        self.stop_button.grid(column=2, row=5, sticky='e')

        self.stop_button = Button(self.master, text="Settings", command=lambda: self.change_settings())
        self.stop_button.grid(column=3, row=5, sticky='e')

        self.state_button = Button(self.master, text="Open channels", command=lambda: self.change_channel_states())
        self.state_button.grid(column=4, row=5, sticky='e')
        self.state_button.config(text="Close channels")

        self.status_label = Label(self.master, text="")
        self.status_label.grid(column=1, row=6, sticky='w', columnspan=5)

        self.quit_button = Button(self.master, text="Exit", command=lambda: self.quit_program())
        self.quit_button.grid(column=5, row=8, sticky='e')

        self.plot_currents()
    # functions

    def ask_directory(self):
        dirtext = "Test"
        self.data_folder = tkFileDialog.askdirectory(parent=root, initialdir='/home/', title=dirtext)
        self.data_dir_entry.delete(0, 'end')
        self.data_dir_entry.insert(0, self.data_folder)

    def change_settings(self):

        t = Toplevel(self.master)
        t.wm_title("Change settings.")
        device0_label = Label(t, text="Current limit:")
        device0_label.grid(column=1, row=1, sticky='w', columnspan=6)
        ch1_current_label0 = Label(t, text="Current 1:")
        ch1_current_label0.grid(column=1, row=3, sticky='e')
        self.ch1_current_limit_entry = Entry(t, width=6)
        self.ch1_current_limit_entry.grid(column=2, row=3, sticky='e')
        self.ch1_current_limit_entry.insert(0, self.ch1_current_limit)
        ch1_current_label = Label(t, text="A")
        ch1_current_label.grid(column=3, row=3, sticky='e')

        # CH2
        ch2_current_label0 = Label(t, text="Current 2:")
        ch2_current_label0.grid(column=1, row=4, sticky='e')
        self.ch2_current_limit_entry = Entry(t, width=6)
        self.ch2_current_limit_entry.grid(column=2, row=4, sticky='e')
        self.ch2_current_limit_entry.insert(0, self.ch2_current_limit)
        ch2_current_label = Label(t, text="A")
        ch2_current_label.grid(column=3, row=4, sticky='e')

        data_dir_label0 = Label(t, text="Data directory:")
        data_dir_label0.grid(column=1, row=5, sticky='w')

        self.data_dir_entry = Entry(t, width=18)
        self.data_dir_entry.grid(column=1, row=6, sticky='w')
        self.data_dir_entry.insert(0, self.data_folder)

        cont_trig_button = Button(t, text="Browse", command=lambda: self.ask_directory(), width=5)
        cont_trig_button.grid(column=3, row=6, sticky='e', columnspan=2)

        self.save_data_var = IntVar()
        self.save_data_var.set(self.save_data)
        Checkbutton(t, text="Save data", variable=self.save_data_var).grid(column=1, row=7, sticky=W)

        ok_button = Button(t, text="Ok", command=lambda: self.save_settings(t))
        ok_button.grid(column=1, row=8, sticky='e')
        cancel_button = Button(t, text="Cancel", command=t.destroy)
        cancel_button.grid(column=2, row=8, sticky='e')

    def change_mode(self, mode):
        if mode == "start":
            self.mode = 1
            if self.save_data:
                self.status_label.config(text="Running. Saving data.")
            else:
                self.status_label.config(text="Running.")
            self.update_currents()
        if mode == "stop":
            self.mode = 0
            self.status_label.config(text="Stopped.")

    def change_channel_states(self, state=""):
        if state == "off":
            self.PSU_interface.set_outputs_off()
            self.state_button.config(text="Open channels")
        elif state == "on":
            self.PSU_interface.set_outputs_on()
            self.state_button.config(text="Close channels")
        elif state == "":
            if self.ch_output_state == 0:
                self.PSU_interface.set_outputs_on()
                self.ch_output_state = 1
                self.state_button.config(text="Close channels")
            elif self.ch_output_state == 1:
                self.PSU_interface.set_outputs_off()
                self.ch_output_state = 0
                self.state_button.config(text="Open channels")

    def check_channel_states(self):
        states = self.PSU_interface.req_output_states()
        if states[0] == 0:
            self.ch1_state_label.config(text="Off")
        elif states[0] == 1:
            self.ch1_state_label.config(text="On")

        if states[1] == 0:
            self.ch2_state_label.config(text="Off")
        elif states[1] == 1:
            self.ch2_state_label.config(text="On")

    def current_limit_reached(self):
        self.change_channel_states("off")
        self.ch_current_limit_reached = 1
        self.status_label.config(text="Current limit reached.")

    def update_currents(self):
        if self.mode == 1:
            self.master.after(1000, self.update_currents)

        self.check_channel_states()

        self.ch1_current = self.PSU_interface.req_ch1_current()
        if self.ch1_current >= self.ch1_current_limit:
            self.current_limit_reached()
        self.ch1_history = self.ch1_history[1:]
        self.ch1_history.append(self.ch1_current)
        self.ch1_current_entry.delete(0, 'end')
        self.ch1_current_entry.insert(0, self.ch1_current)

        self.ch2_current = self.PSU_interface.req_ch2_current()
        if self.ch2_current >= self.ch2_current_limit:
            self.current_limit_reached()
        self.ch2_history = self.ch2_history[1:]
        self.ch2_history.append(self.ch2_current)
        self.ch2_current_entry.delete(0, 'end')
        self.ch2_current_entry.insert(0, self.ch2_current)

        ch1_voltage = self.PSU_interface.req_ch1_voltage()
        ch2_voltage = self.PSU_interface.req_ch2_voltage()




        if self.save_data:
            # Save values to a file.
            timestamp = time.strftime("%Y/%m/%d/%H:%M:%S")
            filename = "%s/current_data.dat" % self.data_folder
            if not os.path.exists(os.path.dirname(filename)):
                try:
                    os.makedirs(os.path.dirname(filename))
                except OSError as exc:  # Guard against race condition
                    print "Unable to create directory"

            outf = open(filename, "a")
            outf.write('%s\t%f\t%f\t%f\t%f\n' % (timestamp, ch1_voltage, self.ch1_current, ch2_voltage, self.ch2_current))
            outf.close()


        self.plot_currents()

    def save_settings(self, t):
        self.ch1_current_limit = float(self.ch1_current_limit_entry.get())
        self.ch2_current_limit = float(self.ch2_current_limit_entry.get())
        self.change_mode('stop')
        self.save_data = self.save_data_var.get()
        t.destroy()

    def initialize_plot(self):
        self.fig = plt.figure(figsize=(4, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().grid(column=1, row=7, columnspan=5)

    def plot_currents(self):

        plt.clf()
        self.fig.clear()
        plt.plot(self.ch1_history, label="ch1")
        plt.plot(self.ch2_history, label="ch2")
        plt.legend()
        plt.xlabel('Time[s]', fontsize=7)
        plt.ylabel('Current[A]', fontsize=7)
        plt.grid()
        plt.tick_params(axis='both', which='major', labelsize=7)
        self.canvas.draw()

    def quit_program(self):
        plt.close("all")
        self.master.destroy()

root = Tk()
my_gui = CurrentMonitorInterface(root)
root.mainloop()

