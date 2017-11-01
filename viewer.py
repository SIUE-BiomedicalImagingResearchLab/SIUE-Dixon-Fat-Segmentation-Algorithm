from tkinter import filedialog
from tkinter import simpledialog

import matplotlib.pyplot as plt

from utils import *


class FigureData():
    def __init__(self, primaryImage, secondaryImage, sliceNumber=0, showDiff=True):
        self.primaryImage = primaryImage
        self.secondaryImage = secondaryImage
        self.sliceNumber = sliceNumber
        self.showDiff = showDiff


figuresData = []


def drawFigure(figureData):
    if figureData.showDiff:
        plt.imshow(fuseImageFalseColor(figureData.primaryImage[:, :, figureData.sliceNumber],
                                       figureData.secondaryImage[:, :, figureData.sliceNumber]))
    else:
        plt.imshow(figureData.primaryImage[:, :, figureData.sliceNumber])

    plt.title('Slice %i' % (figureData.sliceNumber))


def keyPress(event):
    global figuresData

    if event.key == 'o':
        primaryImageFilename = filedialog.askopenfilename(initialdir="/", title="Select primary image",
                                                          filetypes=(("Numpy files", "*.npy"), ("All files", "*.*")))
        secondaryImageFilename = filedialog.askopenfilename(initialdir="/", title="Select secondary image",
                                                            filetypes=(("Numpy files", "*.npy"), ("All files", "*.*")))

        primaryImage = np.load(primaryImageFilename)
        secondaryImage = np.load(secondaryImageFilename)

        figuresData.append(FigureData(primaryImage, secondaryImage))
        figureNumber = len(figuresData)
        newFigure = True
    else:
        figureNumber = event.canvas.figure.number
        newFigure = False

    figure = plt.figure(figureNumber)
    plt.pause(0.005)
    figureData = figuresData[figureNumber - 1]

    if event.key == 'a':
        figureData.sliceNumber = max(figureData.sliceNumber - 1, 0)
    elif event.key == 'd':
        figureData.sliceNumber = min(figureData.sliceNumber + 1, figureData.primaryImage.shape[2] - 1)
    elif event.key == 'x':
        figureData.showDiff = not figureData.showDiff
    elif event.key == 'z':
        # slice = simpledialog.askinteger("Enter slice number", "Enter slice number")
        slice = 164

        figureData.sliceNumber = min(max(slice, 0), figureData.primaryImage.shape[2] - 1)

        # figure = plt.figure(figureNumber)
    elif not newFigure:
        return

    plt.clf()
    drawFigure(figureData)

    if newFigure:
        figure.canvas.mpl_connect('key_press_event', keyPress)

    figure.canvas.draw()


fig, ax = plt.subplots()
fig.canvas.mpl_connect('key_press_event', keyPress)

plt.show()
