from math import floor
import os
from copy import copy
from tkinter import filedialog
import tkinter as tk
import customtkinter
import numpy as np
from PIL import ImageTk
import nibabel as nib
import matplotlib.pyplot as plt

from edges_and_curvatures_algorithms.curvature_algo import curvature_algo
from edges_and_curvatures_algorithms.edges_algo import edges_algo
from filters.mean_filter import mean_filter
from filters.median_filter import median_filter
from final_algo.laplacian_coords import laplacian_coords
from final_algo.subsampling import subsampling
from registration_algorithms.affine import affine_registration_algo
from segmentation_algorithms.isodata import isodataAlgo
from segmentation_algorithms.thresholding import algoThresholding
from segmentation_algorithms.k_means import algoKMeans
from segmentation_algorithms.region_growing import algoRegionGrowing
from standarization_algorithms.h_matching import h_matching
from standarization_algorithms.rescalling_std import rescaling_std
from standarization_algorithms.white_stripe_std import white_stripe_std
from standarization_algorithms.zscore_std import z_score_std

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        #important variables
        self.file_path = "" # path to nifti file
        self.image_showing_path = "./images/canvas.png" # image showing on canvas
        self.current_data = None # nifti file loaded and gotten data with get_fdata()
        self.current_position_in_history = 0
        self.history_data = [] # all data gotten with get_fdata(), the first beign the original data deprecated is a array of three dim arrays (fdatas)
        #self.history_data_foreground = []  # array of three dim arrays (fdatas) of foreground annotations
        #self.history_data_background = []  # array of three dim arrays (fdatas) of background annotations
        self.points_drawings = [] #example [self.current_slice,self.start_x,self.start_y,0,'Red'] o [self.current_slice,self.start_x,self.start_y,1,'Red'] o [self.current_slice,self.start_x,self.start_y,2,'Red']
        self.points_drawings_translated_to_fdata = [] #translated draw points with the original matrix: [[1,2,3],[4,5,6]]
        self.points_drawings_translated_to_fdata_foreground = [] #translated draw points with the original matrix: [[1,2,3,'Red'],[4,5,6,'Red']]
        self.points_drawings_translated_to_fdata_background = [] #translated draw points with the original matrix: [[1,2,3,'Pink'],[4,5,6,'Pink']]
        self.points_drawings_labels = []
        self.image = None
        self.inital_slice = 0
        self.current_slice = self.inital_slice

        # creation of canvas
        self.canvas = tk.Canvas(self.master, width=512, height=512)
        self.canvas.grid(row=0, column=1, padx=20, pady=(20,20))
        self.canvas.create_image(0,0,anchor=tk.NW,image = self.image)
        self.fig_size_images = 10

        # Configura los eventos del mouse
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw_on_image)

        self.start_x = None
        self.start_y = None

        self.my_pad_y = 2



        self.label_options_foreground_color = "Red-Foreground"
        self.label_options_background_color = "Pink-Background"
        self.foreground_color = "Red"
        self.background_color = "Pink"
        self.current_color = self.foreground_color
        self.current_view_mode = "Axial"

        # configure window
        self.title("GUI - Medical Images Segmentation")
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}")
        self.geometry("+0+0")  # Set the window position to the top-left corner

        # configure grid layout, only column one expands
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1, 2,3,4,5), weight=1)

        # create sidebar frame with widgets
        self.left_sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.left_sidebar_frame.grid(row=0, column=0, rowspan=23, sticky="nsew")
        self.left_sidebar_frame.grid_rowconfigure(26, weight=1)

        # welcome text
        self.logo_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Welcome!", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # upload file button
        self.upload_image_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.upload_file_and_show_first_image_event, text="Upload NIFTI")
        self.upload_image_button.grid(row=1, column=0, padx=20, pady=self.my_pad_y)

        # welcome text
        self.algos_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Avaliable Algos:", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.algos_label.grid(row=2, column=0, padx=20, pady=(self.my_pad_y , self.my_pad_y))

        # run_segmentation_button button
        self.run_thresholding_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_thresholding_event, text="Run Thresholding")
        self.run_thresholding_button.grid(row=4, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_isodata_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_isodata_event, text="Run Isodata")
        self.run_isodata_button.grid(row=5, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_region_growing_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_region_growing_event, text="Run Region Growing")
        self.run_region_growing_button.grid(row=6, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_k_means_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_k_means_event, text="Run K Means")
        self.run_k_means_button.grid(row=7, column=0, padx=20, pady=self.my_pad_y)

        # avaliable filters label
        self.avaliable_filters_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Avaliable Filters:", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.avaliable_filters_label.grid(row=8, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # run_segmentation_button button
        self.run_mean_filter_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_mean_filter_event, text="Run Mean Filter")
        self.run_mean_filter_button.grid(row=9, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_median_filter_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_median_filter_event, text="Run Median Filter")
        self.run_median_filter_button.grid(row=10, column=0, padx=20, pady=self.my_pad_y)

        # avaliable standarization algos label
        self.avaliable_std_algos_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Standarization:",
                                                              font=customtkinter.CTkFont(size=20, weight="bold"))
        self.avaliable_std_algos_label.grid(row=11, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # run_segmentation_button button
        self.run_rescaling_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_rescaling_std_event, text="Run Rescaling Std.")
        self.run_rescaling_button.grid(row=12, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_zscore_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_zscore_std_event, text="Run Zscore Std.")
        self.run_zscore_button.grid(row=13, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_histogram_matching_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_h_matching_std_event, text="Run H. Matching Std.")
        self.run_histogram_matching_button.grid(row=14, column=0, padx=20, pady=self.my_pad_y)

        # run_segmentation_button button
        self.run_white_stripe_button = customtkinter.CTkButton(self.left_sidebar_frame, command=self.run_white_stripe_std_event, text="Run White Stripe Std.")
        self.run_white_stripe_button.grid(row=15, column=0, padx=20, pady=self.my_pad_y)

        # Edge & Curvature algos label
        self.avaliable_edges_and_curvatures = customtkinter.CTkLabel(self.left_sidebar_frame, text="Edge & Curvature:",
                                                              font=customtkinter.CTkFont(size=20, weight="bold"))
        self.avaliable_edges_and_curvatures.grid(row=16, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # run_edges_algo_button button
        self.run_edges_algo_button = customtkinter.CTkButton(self.left_sidebar_frame,
                                                               command=self.run_edges_algo_event,
                                                               text="Run Edges Algo.")
        self.run_edges_algo_button.grid(row=17, column=0, padx=20, pady=self.my_pad_y)

        # run_curvature_algo_button button
        self.run_curvature_algo_button = customtkinter.CTkButton(self.left_sidebar_frame,
                                                               command=self.run_curvature_algo_event,
                                                               text="Run Curvatures Algo.")
        self.run_curvature_algo_button.grid(row=18, column=0, padx=20, pady=self.my_pad_y)

        # registration label
        self.registration_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Registration:",
                                                              font=customtkinter.CTkFont(size=20, weight="bold"))
        self.registration_label.grid(row=19, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # run_afinne_registration_button
        self.run_affine_registration_button = customtkinter.CTkButton(self.left_sidebar_frame,
                                                               command=self.run_affine_registration_event,
                                                               text="Run Affine Registration")
        self.run_affine_registration_button.grid(row=20, column=0, padx=20, pady=self.my_pad_y)

        # Laplacian coords label
        self.laplacian_coordinates_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Laplacian Coords:",
                                                              font=customtkinter.CTkFont(size=20, weight="bold"))
        self.laplacian_coordinates_label.grid(row=21, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # run_laplacian_coords_button button
        self.run_laplacian_coords_button = customtkinter.CTkButton(self.left_sidebar_frame,
                                                               command=self.run_laplacian_coords_event,
                                                               text="Run Laplacian Coords")
        self.run_laplacian_coords_button.grid(row=22, column=0, padx=20, pady=self.my_pad_y)

        # run_laplacian_coords_button button
        self.run_subsampling_button = customtkinter.CTkButton(self.left_sidebar_frame,
                                                               command=self.run_subsampling_event,
                                                               text="Run Subsampling")
        self.run_subsampling_button.grid(row=23, column=0, padx=20, pady=self.my_pad_y)

        # appareance mode label
        self.appearance_mode_label = customtkinter.CTkLabel(self.left_sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=24, column=0, padx=20, pady=10)
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.left_sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=25, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))







        # create tabview
        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, rowspan=11, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.tabview.add("Paint")
        self.tabview.add("Info")
        self.tabview.tab("Paint").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Info").grid_columnconfigure(0, weight=1)

        # choose color text
        self.choose_color_label = customtkinter.CTkLabel(self.tabview.tab("Paint"), text="Labeling options:",
                                                         font=customtkinter.CTkFont(size=20, weight="normal"))
        self.choose_color_label.grid(row=0, column=0, padx=20, pady=(20, self.my_pad_y))

        # color options
        self.colors_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Paint"), dynamic_resizing=False,
                                                             values=[self.label_options_foreground_color, self.label_options_background_color],
                                                             command=self.color_change_event)
        self.colors_optionmenu.grid(row=1, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))



        # choose color text
        self.choose_view_label = customtkinter.CTkLabel(self.tabview.tab("Paint"), text="Choose a view:",
                                                        font=customtkinter.CTkFont(size=20, weight="normal"))
        self.choose_view_label.grid(row=2, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # view mode of the file
        self.view_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Paint"), dynamic_resizing=False,
                                                           values=["Axial", "Coronal", "Sagital"],
                                                           command=self.change_view_event)
        self.view_optionmenu.grid(row=3, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # Slice view f the file
        self.label = customtkinter.CTkLabel(self.tabview.tab("Paint"), text="Current Slice: 0")
        self.label.grid(row=4, column=0, padx=20, pady=(20, 0))

        self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_=0, to=0, command=self.update_label,
                                              width=120)
        self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))

        # Creamos un frame interno
        self.back_forth_buttons_frame = tk.Frame(self.tabview.tab("Paint"), bg=self.tabview.tab("Paint")._bg_color,
                                                 width=350, height=150)
        self.back_forth_buttons_frame.grid(row=6, column=0, padx=0, pady=(self.my_pad_y, 20))

        self.button_back = tk.Button(self.back_forth_buttons_frame, width=20, command=self.go_back_in_history)
        self.img_back = tk.PhotoImage(file="./images/go-back.png")  # asegúrate de usar "/" en lugar de "\"
        # Redimensionamos la imagen
        self.resized_img_back = self.img_back.subsample(20, 20)  # Ajusta los factores para redimensionar
        self.button_back.config(image=self.resized_img_back)
        self.button_back.grid(row=0, column=0, padx=(5, 5))

        self.button_forth = tk.Button(self.back_forth_buttons_frame, width=20, command=self.go_forth_in_history)
        self.img_forth = tk.PhotoImage(file="./images/go-forth.png")  # asegúrate de usar "/" en lugar de "\"
        # Redimensionamos la imagen
        self.resized_img_forth = self.img_forth.subsample(20, 20)  # Ajusta los factores para redimensionar
        self.button_forth.config(image=self.resized_img_forth)
        self.button_forth.grid(row=0, column=1, padx=(5, 5),pady=self.my_pad_y )

        # run_segmentation_button button
        self.clear_history_button = customtkinter.CTkButton(self.tabview.tab("Paint"), command=self.clear_paintings,
                                                            text="Clear Paintings")
        self.clear_history_button.grid(row=7, column=0, padx=20, pady=self.my_pad_y)

        # Program state label
        self.state_of_program_label = customtkinter.CTkLabel(self.tabview.tab("Paint"), text="Program State: ",
                                                             font=customtkinter.CTkFont(size=20, weight="normal"))
        self.state_of_program_label.grid(row=8, column=0, padx=20, pady=(self.my_pad_y, self.my_pad_y))

        # Program state label image
        self.state_of_program_label_img = tk.Button(self.tabview.tab("Paint"), width=20)
        self.state_image = tk.PhotoImage(file="./images/ready.png")  # asegúrate de usar "/" en lugar de "\"
        # Redimensionamos la imagen
        self.resized_state_image = self.state_image.subsample(20, 20)  # Ajusta los factores para redimensionar
        self.state_of_program_label_img.config(image=self.resized_state_image)
        self.state_of_program_label_img.grid(row=9, column=0, padx=(5, 5))

        # download annotations button
        self.download_annotations_button = customtkinter.CTkButton(self.tabview.tab("Paint"),
                                                                   command=self.download_annotations_event,
                                                                   text="Download Annotations")
        self.download_annotations_button.grid(row=10, column=0, padx=20, pady=(350, self.my_pad_y))

        # download current matrix button
        self.download_file_button = customtkinter.CTkButton(self.tabview.tab("Paint"),
                                                            command=self.download_nifti_event, text="Download NIFTI")
        self.download_file_button.grid(row=11, column=0, padx=20, pady=self.my_pad_y)

    def go_forth_in_history(self):
        print("go_forth_in_history")
        if len(self.history_data) > self.current_position_in_history+1:
            self.current_data = self.history_data[self.current_position_in_history + 1]
            self.current_position_in_history += 1
            self.save_image_paint_canvas()
        else:
            print("Cant go forth in history, bc there is no more")

    def go_back_in_history(self):
        print("go_back_in_history")
        if self.current_position_in_history > 0:
            self.current_data = self.history_data[self.current_position_in_history - 1]
            self.current_position_in_history -= 1
            self.save_image_paint_canvas()
        else:
            print("Cant go back in history, bc there is no more")


    def change_program_state_label(self,state):
        self.state_image = None
        if state == "loading":
            self.state_image = tk.PhotoImage(file="./images/loading.png")  # asegúrate de usar "/" en lugar de "\"
        elif state == "ready":
            self.state_image = tk.PhotoImage(file="./images/ready.png")  # asegúrate de usar "/" en lugar de "\"
        else:
            return ValueError
        # Redimensionamos la imagen
        self.resized_state_image = self.state_image.subsample(20, 20)  # Ajusta los factores para redimensionar
        self.state_of_program_label_img.config(image=self.resized_state_image)
        self.state_of_program_label_img.update()

    def clear_paintings(self):
        # clean history
        self.points_drawings.clear()
        self.points_drawings_translated_to_fdata.clear()
        self.points_drawings_translated_to_fdata_background.clear()
        self.points_drawings_translated_to_fdata_foreground.clear()

        self.update_label(self.current_slice)

    def download_annotations_event(self):
        print("Downloading annotations...")

        # Create a mask to keep track of visited voxels
        mask = np.zeros_like(self.current_data, dtype=np.uint8)

        for x, y, z, m in self.points_drawings_translated_to_fdata_foreground:
            mask[x][y][z] = -200

        for x, y, z, m in self.points_drawings_translated_to_fdata_background:
            mask[x][y][z] = -100

        img = nib.load(self.file_path)
        final_img = nib.Nifti1Image(mask, img.affine)
        folder_path = filedialog.askdirectory(
            initialdir="."
        )
        nib.save(final_img, os.path.join(folder_path, 'annotations.nii.gz'))

    def download_nifti_event(self):
        print("Downloading nifti")
        img = nib.load(self.file_path)
        # Convert boolean data type to uint8
        if self.current_data.dtype == bool:
            self.current_data = self.current_data.astype(np.uint8)
        final_img = nib.Nifti1Image(self.current_data, img.affine)
        folder_path = filedialog.askdirectory(
            initialdir="."
        )
        nib.save(final_img, os.path.join(folder_path, 'new_data.nii.gz'))
    # it is called everytime the slicer is moved.
    # it repaints all the drawings made in a specific slice
    def repaint_points_drawings(self):
        for three_d_cords in self.points_drawings:
            if self.current_view_mode == 'Coronal' and 0 == three_d_cords[3] and self.current_slice == three_d_cords[0]:#coronal view mode
                print("Coronal")
                self.canvas.create_oval(three_d_cords[1], three_d_cords[2], three_d_cords[1], three_d_cords[2], outline=three_d_cords[4].lower(), width=1)
            elif self.current_view_mode == 'Sagital' and 1 == three_d_cords[3] and self.current_slice == three_d_cords[1]:#sagital view mode
                print("Sagital")
                self.canvas.create_oval(three_d_cords[0], three_d_cords[2], three_d_cords[0], three_d_cords[2], outline=three_d_cords[4].lower(), width=1)
            elif self.current_view_mode == 'Axial' and 2 == three_d_cords[3] and self.current_slice == three_d_cords[2]:#axial view mode
                print("Axial")
                self.canvas.create_oval(three_d_cords[0], three_d_cords[1], three_d_cords[0], three_d_cords[1], outline=three_d_cords[4].lower(), width=1)
            #print(self.points_drawings)
    def update_label(self, value):
        self.label.configure(text="Current Slice: {}".format(int(value)))
        self.current_slice = int(value)

        print(self.current_view_mode)
        # Create figure and axes
        '''
        IMPORTANT: THIS FUNCTION RESIZES THE ACTUAL DATA, IN SAVEFIG, I AM CROPPING THE BLANCK FRAME
        -> fig.savefig("./images/canvas.png", bbox_inches='tight', pad_inches=0)  # Adjust bounding box
        TO TRANSLATE THE DRAWINGS COORDINATES, THE WIDTH, HEIGHT, OF THE SAVED IMAGE MUST BE DIVIDED BY THE WIDTH, HEIGHT
        OF THE DATA.SHAPE[0], DATA.SHAPE[1] AND THEN DIVIE THE RESULT WITH WIDTH, HEIGHT OF EACH COORD OF THE DRAWINGS
        '''
        fig, axes = plt.subplots(1, 1, figsize=(self.fig_size_images, self.fig_size_images),dpi=100)

        # Remove innnecesario info
        axes.axis('off')



        # Display initial slices
        ax0_img = None
        if self.current_view_mode == 'Coronal':
            ax0_img = axes.imshow(self.current_data[self.current_slice, :, :])
        elif self.current_view_mode == 'Sagital':
            ax0_img = axes.imshow(self.current_data[:, self.current_slice, :])
        elif self.current_view_mode == 'Axial':
            ax0_img = axes.imshow(self.current_data[:, :, self.current_slice])


        # Save the figure
        fig.savefig("./images/canvas.png", bbox_inches='tight', pad_inches=0)  # Adjust bounding box

        self.image = ImageTk.PhotoImage(file=self.image_showing_path)

        self.canvas.create_image(0,0,anchor=tk.NW,image = self.image)

        self.canvas.config(width=self.image.width(), height=self.image.height())
        self.canvas.update()

        self.repaint_points_drawings()

    def start_drawing(self, event):
        # Guarda las coordenadas iniciales del dibujo
        self.start_x = event.x
        self.start_y = event.y

    def draw_on_image(self, event):
        # Dibuja una línea desde las coordenadas iniciales hasta las coordenadas actuales
        if self.start_x is not None and self.start_y is not None:
            x, y = event.x, event.y
            self.canvas.create_oval(self.start_x, self.start_y,self.start_x, self.start_y, outline=self.current_color.lower(), width=1)
            self.start_x = x
            self.start_y = y
            print(self.start_x, self.start_y)
            #print("shape data:")
            #print(self.current_data.shape[0])
            # I will add all the points referencing fdata to paint again the points if necesseray
            '''
            1. Matrix Representation of Images:
            In many image processing libraries and standards (like NumPy in Python, which is commonly used in scientific computing),
            images are treated as arrays or matrices. In this representation:
            The first index (y) corresponds to the row (vertical position).
            The second index (x) corresponds to the column (horizontal position).
            '''
            if self.current_view_mode == "Coronal":
                if self.current_color == self.foreground_color:
                    self.points_drawings.append([self.current_slice, self.start_x, self.start_y, 0, self.foreground_color])
                    #self.points_drawings_translated_to_fdata_foreground.append([self.current_slice, self.start_y // (self.image.height() // self.current_data.shape[2]),self.start_x // (self.image.width() // self.current_data.shape[1]),self.foreground_color])
                    self.points_drawings_labels.append('F')
                if self.current_color == self.background_color:
                    self.points_drawings.append([self.current_slice, self.start_x, self.start_y, 0, self.background_color])
                    #self.points_drawings_translated_to_fdata_background.append([self.current_slice, self.start_y // (self.image.height() // self.current_data.shape[2]),self.start_x // (self.image.width() // self.current_data.shape[1]), self.background_color])
                    self.points_drawings_labels.append('B')
                self.points_drawings_translated_to_fdata.append([self.current_slice,self.start_y//(self.image.height()//self.current_data.shape[2]),self.start_x//(self.image.width()//self.current_data.shape[1])])
            if self.current_view_mode == "Sagital":
                if self.current_color == self.foreground_color:
                    self.points_drawings.append([self.start_x, self.current_slice, self.start_y, 1, self.foreground_color])
                    #self.points_drawings_translated_to_fdata_foreground.append([self.start_y // (self.image.height() // self.current_data.shape[0]), self.current_slice,self.start_x // (self.image.width() // self.current_data.shape[2]),self.foreground_color])
                    self.points_drawings_labels.append('F')
                if self.current_color == self.background_color:
                    self.points_drawings.append([self.start_x, self.current_slice, self.start_y, 1, self.background_color])
                    #self.points_drawings_translated_to_fdata_background.append([self.start_y // (self.image.height() // self.current_data.shape[0]), self.current_slice, self.start_x // (self.image.width() // self.current_data.shape[2]),self.background_color])
                    self.points_drawings_labels.append('B')
                self.points_drawings_translated_to_fdata.append([self.start_y//(self.image.height()//self.current_data.shape[0]),self.current_slice,self.start_x//(self.image.width()//self.current_data.shape[2])])
            if self.current_view_mode == "Axial":
                if self.current_color == self.foreground_color:
                    self.points_drawings.append([self.start_x, self.start_y, self.current_slice, 2, self.foreground_color])
                    #self.points_drawings_translated_to_fdata_foreground.append([round(self.start_y / round(self.image.height() / self.current_data.shape[1])),round(self.start_x / round(self.image.width() / self.current_data.shape[0])),self.current_slice, self.foreground_color])
                    self.points_drawings_labels.append('F')
                if self.current_color == self.background_color:
                    self.points_drawings.append([self.start_x, self.start_y, self.current_slice, 2, self.background_color])
                    #self.points_drawings_translated_to_fdata_background.append([round(self.start_y / round(self.image.height() / self.current_data.shape[1])), round(self.start_x / round(self.image.width() / self.current_data.shape[0])), self.current_slice,self.background_color])
                    self.points_drawings_labels.append('B')
                self.points_drawings_translated_to_fdata.append([floor(self.start_y/floor(self.image.height()/self.current_data.shape[1])),floor(self.start_x/floor(self.image.width()/self.current_data.shape[0])),self.current_slice])
        #print("Points drawings: ",self.points_drawings)
        #print("fdata: ",self.points_drawings_translated_to_fdata)
        #print("fdata background: ",self.points_drawings_labels)
        #print("fdata foreground: ",self.points_drawings_labels)
    def color_change_event(self,chosen_color):
        print(chosen_color)
        if chosen_color == self.label_options_foreground_color:
            self.current_color = self.foreground_color
        elif chosen_color == self.label_options_background_color:
            self.current_color = self.background_color
        else:
            raise Exception("Color no valid")
    def change_view_event(self, view_mode):
        print("change view event",view_mode)
        # Create figure and axes
        '''
        IMPORTANT: THIS FUNCTION RESIZES THE ACTUAL DATA, IN SAVEFIG, I AM CROPPING THE BLANCK FRAME
        -> fig.savefig("./images/canvas.png", bbox_inches='tight', pad_inches=0)  # Adjust bounding box
        TO TRANSLATE THE DRAWINGS COORDINATES, THE WIDTH, HEIGHT, OF THE SAVED IMAGE MUST BE DIVIDED BY THE WIDTH, HEIGHT
        OF THE DATA.SHAPE[0], DATA.SHAPE[1] AND THEN DIVIE THE RESULT WITH WIDTH, HEIGHT OF EACH COORD OF THE DRAWINGS
        '''
        fig, axes = plt.subplots(1, 1, figsize=(self.fig_size_images, self.fig_size_images),dpi=100)

        # Remove innnecesario info
        axes.axis('off')

        self.current_view_mode = view_mode

        # Display initial slices
        ax0_img = None
        if view_mode == 'Coronal':
            # Reset the current slice
            self.slider.destroy()
            self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_= 0,to=self.current_data.shape[0], command=self.update_label,
                                                  width=120)
            self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))
            self.update_label(self.current_data.shape[0] // 2)
            ax0_img = axes.imshow(self.current_data[self.current_slice, :, :])
        elif view_mode == 'Sagital':
            # Reset the current slice
            self.slider.destroy()
            self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_= 0,to=self.current_data.shape[1], command=self.update_label,
                                                  width=120)
            self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))
            self.update_label(self.current_data.shape[1] // 2)
            ax0_img = axes.imshow(self.current_data[:, self.current_slice, :])
        elif view_mode == 'Axial':
            # Reset the current slice
            self.slider.destroy()
            self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_= 0,to=self.current_data.shape[2], command=self.update_label,
                                                  width=120)
            self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))
            self.update_label(self.current_data.shape[2] // 2)
            ax0_img = axes.imshow(self.current_data[:, :, self.current_slice])


        # Save the figure
        fig.savefig("./images/canvas.png", bbox_inches='tight', pad_inches=0)  # Adjust bounding box

        self.image = ImageTk.PhotoImage(file=self.image_showing_path)

        self.canvas.create_image(0,0,anchor=tk.NW,image = self.image)

        self.canvas.config(width=self.image.width(), height=self.image.height())
        self.canvas.update()

        self.repaint_points_drawings()


    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)


    def upload_file_and_show_first_image_event(self):
        print("upload_file_event click")

        self.file_path = filedialog.askopenfilename(initialdir=".")

        # clean history
        self.points_drawings.clear()
        self.points_drawings_translated_to_fdata.clear()
        #In case a file can't be opened
        try:
            img_aux = nib.load(self.file_path)
        except:
            return 0
        self.current_data = img_aux.get_fdata()
        print(self.current_data.shape)



        self.history_data.append(self.current_data)

        self.current_view_mode = "Axial"
        self.save_image_paint_canvas()

        # Create figure and axes

    def save_image_paint_canvas(self):
        print("change view event",self.current_view_mode)
        # Create figure and axes
        '''
        IMPORTANT: THIS FUNCTION RESIZES THE ACTUAL DATA, IN SAVEFIG, I AM CROPPING THE BLANCK FRAME
        -> fig.savefig("./images/canvas.png", bbox_inches='tight', pad_inches=0)  # Adjust bounding box
        TO TRANSLATE THE DRAWINGS COORDINATES, THE WIDTH, HEIGHT, OF THE SAVED IMAGE MUST BE DIVIDED BY THE WIDTH, HEIGHT
        OF THE DATA.SHAPE[0], DATA.SHAPE[1] AND THEN DIVIE THE RESULT WITH WIDTH, HEIGHT OF EACH COORD OF THE DRAWINGS
        '''
        fig, axes = plt.subplots(1, 1, figsize=(self.fig_size_images, self.fig_size_images),dpi=100)

        # Remove innnecesario info
        axes.axis('off')

        self.current_view_mode = self.current_view_mode

        # Display initial slices
        ax0_img = None
        if self.current_view_mode == 'Coronal':
            # Reset the current slice
            self.slider.destroy()
            self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_= 0,to=self.current_data.shape[0], command=self.update_label,
                                                  width=120)
            self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))
            self.update_label(self.current_data.shape[0] // 2)
            ax0_img = axes.imshow(self.current_data[self.current_slice, :, :])
        elif self.current_view_mode == 'Sagital':
            # Reset the current slice
            self.slider.destroy()
            self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_= 0,to=self.current_data.shape[1], command=self.update_label,
                                                  width=120)
            self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))
            self.update_label(self.current_data.shape[1] // 2)
            ax0_img = axes.imshow(self.current_data[:, self.current_slice, :])
        elif self.current_view_mode == 'Axial':
            # Reset the current slice
            self.slider.destroy()
            self.slider = customtkinter.CTkSlider(self.tabview.tab("Paint"), from_= 0,to=self.current_data.shape[2], command=self.update_label,
                                                  width=120)
            self.slider.grid(row=5, column=0, padx=20, pady=(0, 20))
            self.update_label(self.current_data.shape[2] // 2)
            ax0_img = axes.imshow(self.current_data[:, :, self.current_slice])


        # Save the figure
        fig.savefig("./images/canvas.png", bbox_inches='tight', pad_inches=0)  # Adjust bounding box

        self.image = ImageTk.PhotoImage(file=self.image_showing_path)

        self.canvas.create_image(0,0,anchor=tk.NW,image = self.image)

        self.canvas.config(width=self.image.width(), height=self.image.height())
        self.canvas.update()

        self.repaint_points_drawings()

    def run_thresholding_event(self):
        print("run_thresholding_event click")
        tau_input = customtkinter.CTkInputDialog(text="Type in a tau:", title="Tau dialog")
        input_value = tau_input.get_input()
        self.change_program_state_label("loading")
        try:
            # Convert the input to an integer
            tau_value = int(input_value)
            # Call the thresholding function with the current data and the user-provided threshold
            new_data = algoThresholding(copy(self.current_data), tau_value)
            self.current_data = new_data
            self.history_data.append(new_data)
            self.current_position_in_history += 1
            self.save_image_paint_canvas()
            self.change_program_state_label("ready")
        except ValueError:
            print("Invalid input: Please enter an integer value for tau.")
    '''
    IMPORTANT:
        THERE MUST BE A FUNCTION THAT CHECKS THAT SELF.CURRENT_DATA IS NOT ONLY TRUE AND FALSE
    '''
    def run_isodata_event(self):
        print("run_isodata_event click")
        print("An example of what is inside of data is: ",str(self.current_data[0][0][0]))
        self.change_program_state_label("loading")
        if str(self.current_data[0][0][0]) != 'False' and str(self.current_data[0][0][0]) != 'True':
            new_data = isodataAlgo(copy(self.current_data))
            self.current_data = new_data
            self.history_data.append(new_data)
            self.current_position_in_history += 1
            self.save_image_paint_canvas()
            self.change_program_state_label("ready")


    def run_region_growing_event(self):
        print("run_region_growing_event click")
        intensity_tolerance_input = customtkinter.CTkInputDialog(text="Type in the number of the intensity difference tolerance:", title="Intensity dialog")
        input_value = intensity_tolerance_input.get_input()
        self.change_program_state_label("loading")
        try:
            intensity_value = int(input_value)
            new_data = algoRegionGrowing(self.current_data, self.points_drawings_translated_to_fdata, intensity_value)
            self.current_data = new_data
            self.history_data.append(new_data)
            self.current_position_in_history += 1
            self.save_image_paint_canvas()
            self.change_program_state_label("ready")
        except ValueError:
            print("Invalid input: Please enter an integer value for intensity difference tolerance")




    def run_k_means_event(self):
        print("run_k_means_event click")
        clusters_input = customtkinter.CTkInputDialog(text="Type in the number of clusters:", title="Clusters dialog")
        input_value = clusters_input.get_input()
        self.change_program_state_label("loading")
        try:
            # Convert the input to an integer
            clusters_value = int(input_value)
            # Call the thresholding function with the current data and the user-provided threshold
            new_data = algoKMeans(copy(self.current_data), clusters_value)
            print("kmeans finished")
            self.current_data = new_data
            self.history_data.append(new_data)
            self.current_position_in_history += 1
            self.save_image_paint_canvas()
            self.change_program_state_label("ready")
        except ValueError:
            print("Invalid input: Please enter an integer value for tau.")


    def run_mean_filter_event(self):
        print("run_mean_filter_event click")
        self.change_program_state_label("loading")
        new_data = mean_filter(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_median_filter_event(self):
        print("run_median_filter_event click")
        self.change_program_state_label("loading")
        new_data = median_filter(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")


    def run_rescaling_std_event(self):
        print("run_rescaling_std_event click")
        self.change_program_state_label("loading")
        new_data = rescaling_std(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_zscore_std_event(self):
        print("run_zscore_std_event click")
        self.change_program_state_label("loading")
        new_data = z_score_std(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_h_matching_std_event(self):
        print("run_h_matching_std_event click")
        file_path = filedialog.askopenfilename(initialdir='.')
        test_new_data = None;
        try:
            test_new_data = nib.load(file_path).get_fdata()
        except nib.filebasedimages.ImageFileError:
            return
        self.change_program_state_label("loading")
        new_data = h_matching(copy(self.current_data),copy(test_new_data),5)
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")



    def run_white_stripe_std_event(self):
        print("run_white_stripe_std_event click")
        self.change_program_state_label("loading")
        new_data = white_stripe_std(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_edges_algo_event(self):
        print("run_edges_algo_event click")
        self.change_program_state_label("loading")
        new_data = edges_algo(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_curvature_algo_event(self):
        print("run_curvature_algo_event")
        self.change_program_state_label("loading")
        new_data = curvature_algo(copy(self.current_data))
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_affine_registration_event(self):
        print("run_affine_registration_event")
        self.change_program_state_label("loading")
        file_image_fixed_path = filedialog.askopenfilename(initialdir='.')
        try:
            new_data = affine_registration_algo(data_rotated_path=self.file_path,data_fixed_path=file_image_fixed_path)
        except:
            return 0
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")

    def run_laplacian_coords_event(self):
        print("run_laplacian_coords_event")
        self.change_program_state_label("loading")
        xB=100
        xF=10
        beta=0.1
        new_data = laplacian_coords(self.current_data,self.points_drawings_translated_to_fdata,self.points_drawings_labels,xB,xF,beta)
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")
        return

    def run_subsampling_event(self):
        print("run_subsampling_event")
        self.change_program_state_label("loading")
        new_data = subsampling(self.current_data)
        self.current_data = new_data
        self.history_data.append(new_data)
        self.current_position_in_history += 1
        self.save_image_paint_canvas()
        self.change_program_state_label("ready")
        return

if __name__ == "__main__":
    app = App()
    app.mainloop()