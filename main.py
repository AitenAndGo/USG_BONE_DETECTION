import cv2 as cv
import numpy as np
import os
import customtkinter
from tkinter import filedialog
from tkinter import messagebox
import threading
import tkinter
from tkinter import ttk
from PIL import ImageTk, Image


# this funkcion finds a line that started in some x and y coordinate
def findLine(X, Y, used, img):
    if X < 0 or X >= img.shape[1] or Y < 0 or Y >= img.shape[0] or used[Y][X]:
        return []

    # if pixel is white then with recursion find all others pixels that are connected and return List with all if theme
    if img[Y][X] > 0:
        used[Y][X] = True
        return [(X, Y)] + findLine(X + 1, Y - 1, used, img) \
            + findLine(X + 1, Y, used, img) \
            + findLine(X + 1, Y + 1, used, img) \
            + findLine(X - 1, Y - 1, used, img) \
            + findLine(X - 1, Y, used, img) \
            + findLine(X - 1, Y + 1, used, img) \
            + findLine(X - 1, Y + 1, used, img) \
            + findLine(X, Y + 1, used, img) \
            + findLine(X + 1, Y + 1, used, img) \
            + findLine(X - 1, Y - 1, used, img) \
            + findLine(X, Y - 1, used, img) \
            + findLine(X + 1, Y - 1, used, img)
    return []


# find all lines in a picture
def findLines(img):
    height, width = img.shape

    used = np.zeros_like(img, dtype=bool)

    lines = []

    # iterate for all pixels in image
    for x in range(width):
        for y in range(height):
            if img[y][x] > 0 and not used[y][x]:
                line = findLine(x, y, used, img)
                if line:
                    lines.append(line)

    return lines


# main function with algorithm to find The Line that represent a Bone in USG Picture
def FindBones(file):
    # read the picture
    img = cv.imread(file, cv.IMREAD_GRAYSCALE)
    height, width = img.shape[:2]

    # blure the picture
    blur = cv.GaussianBlur(img, (11, 11), 5)

    # binarize  the picture to uncover the bone structure
    ret, Threshold = cv.threshold(blur, 70, 255, cv.THRESH_BINARY)

    # setting up coordinates for mask
    leftBottom = (int(0 * width), int(0 * height))
    rightBottom = (int(1 * width), int(0 * height))
    leftTop = (int(0 * width), int(0.3 * height))
    rightTop = (int(1 * width), int(0.3 * height))

    vertices = [leftBottom, rightBottom, rightTop, leftTop]
    vertices = np.array([vertices], dtype=np.int32)
    blank = np.zeros_like(img)
    # fillling our mask with white pixels
    cutPolly = cv.fillConvexPoly(blank, vertices, 255)

    # cutting part of image that is useless
    cutPolly = cv.bitwise_and(Threshold, cutPolly)

    # setting max thickness of Bone structure to avoid noise
    maxThickness = 45
    for x in range(width):
        count = 0
        stack = []
        # going form top to bottom of image to chcech the thickness
        for y in range(height):
            if cutPolly[y][x] > 0:
                count += 1
                stack.append((x, y))
            else:
                if count > maxThickness:
                    for pixel in stack:
                        cutPolly[pixel[1]][pixel[0]] = 0
                count = 0
                stack = []

    # using sobel in y coordinates to find horizontal lines on image
    sobely = cv.Sobel(cutPolly, cv.CV_8U, 0, 1, ksize=11)

    # using erosion to the lines thiner
    kernel = np.ones((3, 3), np.uint8)
    erosion = cv.erode(sobely, kernel, iterations=3)

    blank = np.zeros_like(img)

    # removeing all structures that are not on top, this way we can remove the echo efect
    for x in range(height):
        for y in range(width):
            if erosion[y][x] > 0:
                blank[y][x] = 255
                break

    # boldness of lines
    dilation = cv.dilate(blank, kernel, iterations=1)

    # finding all lines that heve left on image
    lines = []
    lines = findLines(dilation)

    # chooseing the line that is longest
    MainLine = []
    for line in lines:
        if len(line) >= len(MainLine):
            MainLine = line
    final = np.zeros_like(img)

    # coloring the result and displaying it on the original photo to compare the result
    for pixel in MainLine:
        final[pixel[1]][pixel[0]] = 255

    color = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    color[:, :, 0] = img
    color[:, :, 1] = img
    color[:, :, 2] = img

    for pixel in MainLine:
        color[pixel[1]][pixel[0]] = [255, 0, 0]

    return color


# The rest of the program is related only to the GUI, so I will not comment :(
def show_image(image, root):
    for widget in root.winfo_children():
        if isinstance(widget, tkinter.Label):
            widget.destroy()

    image_cv = image

    image_rgb = cv.cvtColor(image_cv, cv.COLOR_BGR2RGB)

    image_pil = Image.fromarray(image_rgb)

    photo = ImageTk.PhotoImage(image_pil)

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    label = tkinter.Label(root, image=photo, text='', anchor='center')
    label.image = photo
    label.grid(row=0, column=0, padx=50, pady=50, sticky="nsew")


def loadImages():
    path = filedialog.askopenfilenames(title="Select Images",
                                       filetypes=(("Image files", "*.jpg;*.jpeg;*.png;*.tif;*.BMP"),
                                                  ("All files", "*.*")))
    if path:
        messagebox.showinfo("Info", f"successfully loaded {len(path)} photos.")

        global filePaths, currentImageIndex, processedImages
        filePaths = path

        currentImageIndex = 0
        processedImages = []
        currentImagename = filePaths[currentImageIndex]
        nameLabel.configure(text=os.path.basename(currentImagename))
        img = cv.imread(filePaths[currentImageIndex], cv.IMREAD_COLOR)
        show_image(img, imageFrame)


def save_images():
    global processedImages
    try:
        foldername = filedialog.askdirectory()
        if foldername:
            if len(processedImages) == 0:
                messagebox.showwarning("Warning", "No images to save")
                return

            for i, img in enumerate(processedImages):
                filename = os.path.join(foldername, f"Bone_Image_{i}.bmp")
                cv.imwrite(filename, img)

            messagebox.showinfo("Info", "Images saved successfully.")
        else:
            messagebox.showwarning("Warning", "No folder selected for saving.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")


def reset():
    global filePaths, currentImageIndex, processedImages, currentImagename
    filePaths = []
    processedImages = []
    currentImageIndex = 0
    currentImagename = ''


def processButtonEvent():
    def process():
        global filePaths, currentImagename

        if len(processedImages) > 0:
            messagebox.showwarning("Warning", "Already Processed")
            return
        else:
            if len(filePaths) == 0:
                messagebox.showwarning("Warning", "No files loaded")
                return

            progressWindow = tkinter.Tk()
            progressWindow.title("Processing Data")

            progress_bar = ttk.Progressbar(progressWindow, orient="horizontal", length=200, mode="determinate")
            progress_bar.pack(pady=10)

            def process_files():
                total_files = len(filePaths)

                for i, file in enumerate(filePaths, 1):
                    img = FindBones(file)
                    processedImages.append(img)
                    progress = int((i / total_files) * 100)
                    progress_bar['value'] = progress
                    progressWindow.update_idletasks()

                global currentImagename
                img = processedImages[0]
                currentImagename = filePaths[0]
                nameLabel.configure(text=os.path.basename(currentImagename))
                show_image(img, imageFrame)

                progressWindow.quit()
                # progressWindow.destroy() // it needs to be checked

            progressWindow.after(100, process_files)
            progressWindow.mainloop()

    process_thread = threading.Thread(target=process)
    process_thread.start()


def nextImage():
    global currentImageIndex, filePaths, processedImages, currentImagename

    if len(filePaths) > 0:
        currentImageIndex += 1
        if currentImageIndex >= len(filePaths):
            currentImageIndex = 0

        if len(processedImages) > 0:
            img = processedImages[currentImageIndex]
            currentImagename = filePaths[currentImageIndex]
            nameLabel.configure(text=os.path.basename(currentImagename))
        else:
            img = cv.imread(filePaths[currentImageIndex], cv.IMREAD_COLOR)
            currentImagename = filePaths[currentImageIndex]
            nameLabel.configure(text=os.path.basename(currentImagename))
        show_image(img, imageFrame)


def previousImage():
    global currentImageIndex, filePaths, processedImages, currentImagename

    if len(filePaths) > 0:
        currentImageIndex -= 1
        if currentImageIndex < 0:
            currentImageIndex = len(filePaths) - 1

        if len(processedImages) > 0:
            img = processedImages[currentImageIndex]
            currentImagename = filePaths[currentImageIndex]
            nameLabel.configure(text=os.path.basename(currentImagename))
        else:
            img = cv.imread(filePaths[currentImageIndex], cv.IMREAD_COLOR)
            currentImagename = filePaths[currentImageIndex]
            nameLabel.configure(text=os.path.basename(currentImagename))
        show_image(img, imageFrame)


filePaths = []
processedImages = []
currentImagename = ''
currentImageIndex = 0

# creating app
app = customtkinter.CTk()
app.geometry("1080x720")
app.title("BonePytector by B.P.")

# configure weights
app.rowconfigure(0, weight=1)
app.columnconfigure(1, weight=1)

# dividing space into 2 frames
optionFrame = customtkinter.CTkFrame(master=app, width=200, height=200)
optionFrame.grid(row=0, column=0, padx=20, pady=20, sticky="nws")
imageFrame = customtkinter.CTkFrame(master=app, width=200, height=200)
imageFrame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

optionFrame.rowconfigure(6, weight=1)

# adding buttons
LoadImagesButton = customtkinter.CTkButton(master=optionFrame, text="Load Images", command=loadImages, height=50,
                                           width=200)
LoadImagesButton.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

saveDataButton = customtkinter.CTkButton(master=optionFrame, text="Save", command=save_images, height=50, width=200)
saveDataButton.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

resetButton = customtkinter.CTkButton(master=optionFrame, text="Reset", command=reset, height=50, width=200)
resetButton.grid(row=5, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

processButton = customtkinter.CTkButton(master=optionFrame, text="Process", command=processButtonEvent, height=50,
                                        width=200, fg_color="#bf1120", hover_color="#91030f")
processButton.grid(row=6, column=0, columnspan=2, padx=20, pady=10, sticky="sew")

backButton = customtkinter.CTkButton(master=optionFrame, text="back", command=previousImage, height=30, width=80)
backButton.grid(row=7, column=0, padx=20, pady=10, sticky="w")

nextButton = customtkinter.CTkButton(master=optionFrame, text="next", command=nextImage, height=30, width=80)
nextButton.grid(row=7, column=1, padx=20, pady=10, sticky="e")

nameLabel = customtkinter.CTkLabel(master=optionFrame, text=f"{currentImagename}", fg_color="transparent")
nameLabel.grid(row=8, column=0, columnspan=2, padx=0, pady=0, sticky="nsew")

app.mainloop()
