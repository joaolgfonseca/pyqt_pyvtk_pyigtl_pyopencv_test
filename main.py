import sys
import vtk
from PyQt5.QtWidgets import QMainWindow, QFrame, QVBoxLayout, QApplication
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util.vtkConstants import VTK_UNSIGNED_CHAR
from vtkmodules.util.numpy_support import numpy_to_vtk
import pyigtl
import numpy as np
import threading as th
import cv2 as cv
import time

# # # # # # # # # # #
# Main window class #
# # # # # # # # # # #


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setup_ui()

    def setup_ui(self):
        self.frame = QFrame()
        self.vl = QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        # Create Image data
        self.image = vtk.vtkImageData()
        self.image.AllocateScalars(VTK_UNSIGNED_CHAR, 1)

        # Create the Image Actor
        self.actor = vtk.vtkImageActor()
        self.actor.GetMapper().SetInputData(self.image)

        self.ren.AddActor(self.actor)
        self.ren.ResetCamera()

        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        self.show()
        self.iren.Initialize()
        self.iren.Start()

    def run(self):
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = ShowImage()
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.getimage_vtk_function)
        self.worker.signal.connect(self.display_vtk_function)
        # Step 6: Start the thread
        self.thread.start()

    @pyqtSlot(vtk.vtkDataArray, list)
    def display_vtk_function(self, new_vtk_array, new_dim):
        self.image.SetDimensions(new_dim[0], new_dim[1], 1)
        # self.image.GetPointData().SetScalars(new_vtk_array)
        self.image.GetPointData().GetScalars().DeepCopy(new_vtk_array)

        self.image.Modified()
        self.ren.ResetCamera()
        self.vtkWidget.GetRenderWindow().Render()


# # # # # # # # # # #
# Show Image class  #
# # # # # # # # # # #


class ShowImage(QObject):

    signal = pyqtSignal(vtk.vtkDataArray, list)
    client = pyigtl.OpenIGTLinkClient(host="127.0.0.1", port=18944)

    def connect_signal(self, function_name):
        self.signal.connect(function_name)

    def getimage_vtk_function(self):
        while True:
            input_message = self.client.wait_for_message("Image_Reference")

            # Numpy to Vtk
            linear_array = np.reshape(input_message.image, (input_message.image.shape[2] * input_message.image.shape[1],
                                                            input_message.image.shape[0]))
            vtk_array = numpy_to_vtk(linear_array, deep=True)
            dim = [input_message.image.shape[2], input_message.image.shape[1]]

            self.signal.emit(vtk_array, dim)

            # (Not working here, CHANGE!!!)
            # Press Q on keyboard to  exit
            if cv.waitKey(25) & 0xFF == ord('q'):
                break

    def getimage_opencv_function(self):
        client = pyigtl.OpenIGTLinkClient(host="127.0.0.1", port=18944)

        while True:
            input_message = client.wait_for_message("Image_Reference")

            # Numpy to opencv
            # img = np.zeros([input_message.image.shape[1], input_message.image.shape[2]], np.uint8)
            # img = input_message.image[0, :, :]

            # Display (can display directly from openigtlink output)
            self.display_opencv_function(input_message.image[0, :, :])

            # Press Q on keyboard to  exit
            if cv.waitKey(25) & 0xFF == ord('q'):
                break

            # print("opencv function")

    def display_opencv_function(self, img):
        # display image
        cv.imshow('test', img)
        # print("opencv display")


if __name__ == "__main__":
    # Qt window + VTK + OpenIGTLink
    app = QApplication(sys.argv)
    window = MainWindow()
    window.run()

    sys.exit(app.exec_())
