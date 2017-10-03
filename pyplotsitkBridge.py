import SimpleITK as sitk
import matplotlib.pyplot as pyplot

def imshow(X, *args, **kwargs):
    nda = sitk.GetArrayFromImage(X)
    pyplot.imshow(nda, *args, **kwargs)