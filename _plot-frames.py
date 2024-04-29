import sys
import MDSplus
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

shot_number = int(sys.argv[1])
tree = MDSplus.Tree('basler', shot_number)

input = tree.BASLER_A.FRAMES
images = [ input.getSegment(i).data() for i in range(input.getNumSegments()) ]
print(f"Number of frames = {len(images)}, Running time = {tree.BASLER_A.RUNNING_TIME.data()}")
npimages = np.array(images)
squeezed_images = np.squeeze(npimages)

print(npimages.shape, squeezed_images.shape)

#frames = []
#fig = plt.figure("Animation")
fig, ax = plt.subplots()

frames_text = []
for i in range(input.getNumSegments()):
    frames = ax.imshow(squeezed_images[i], cmap=cm.Greys_r,animated=True)
    text   = ax.text(x=400, y=450, s=i, color='r', fontsize=14, fontweight='bold') # add text
    
    frames_text.append([frames, text]) # add frames and text

anim = animation.ArtistAnimation(fig, frames_text, interval=500, blit=True, repeat_delay=1000) #interval in millisec

#fig = plt.figure()
#for i in range(input.getNumSegments()):
#    fig.add_subplot(5, 5, i + 1)
#    plt.imshow(images[i], cmap=cm.Greys_r)

plt.show()
