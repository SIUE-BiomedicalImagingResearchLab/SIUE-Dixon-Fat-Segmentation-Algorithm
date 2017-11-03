# This file contains all the constants that will not be regularly changed upon runtime
# It is benficial to developers who want to fine-tune or tweak some parameters to optimize some aspect of the code

# Name of the application, organization that created the application and current version of the application
applicationName = 'Dixon Fat Segmentation Algorithm'
organizationName = 'Southern Illinois University Edwardsville'
version = '1.0.0'

# Force segmentation of data paths selected regardless of if there is already existing data or not
forceSegmentation = False

# Debug option to show the body mask side by side with the fat/water slice combined
showBodyMask = False

# Debug option to save intermediate steps while running algorithm
debug = True

# Debug option to save intermediate steps for N4 bias correction in directory of the subject
debugBiasCorrection = True

# Factor to shrink the volume by when applying the N4 ITK bias correction algorithm
# Should be a number between 1-4
# 4 - fatUpper took 12s, so total would be approx. 12 * 4 = 48s
# 3 - fatUpper took 28s, so total would be approx. 12 * 4 = 112s
# 2 - fatUpper took 80s, so total would be approx. 12 * 4 = 320s ~= 5min
# 1 - fatUpper took 690s, so total would be approx. 12 * 4 = 2760s ~= 46min
shrinkFactor = 4

# Number of clusters for the K-means algorithm for segmenting images
kMeanClusters = 2

# Threshold area for the fat voids mask in abdominal region. This is used to remove objects smaller than this
# threshold when determining the fat voids area.
thresholdAbdominalFatVoidsArea = 30

# Threshold area for the fat voids mask in thoracic region. This is used to remove objects smaller than this
# threshold when determining the fat voids area.
thresholdThoracicFatVoidsArea = 500

# Minimum area of CAT object
# This is used as a threshold to remove small depots of pixels in the CAT
minCATObjectArea = 5

# Minimum area of SCAT object
# This is used as a threshold to remove small depots of pixels in the SCAT
minSCATObjectArea = 5

# Minimum area of VAT object
# This is used as a threshold to remove small depots of pixels in the VAT
minVATObjectArea = 5