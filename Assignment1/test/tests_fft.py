import numpy as np
from scipy.fftpack import fft, ifft, fftfreq
from matplotlib import pyplot as plt

norm_accel_io = np.loadtxt("norm_accel_io.txt")
norm_accel_sun = np.loadtxt("norm_accel_sun.txt")

number_of_points = len(norm_accel_io)
timestep = 10 # seconds

norm_accel_io -= np.mean(norm_accel_io[:,1], axis=0)
norm_accel_sun -= np.mean(norm_accel_sun[:,1], axis=0)

print(norm_accel_io[:,1].mean()) # debugging
print(norm_accel_io.shape) # debugging

# Source - https://stackoverflow.com/a/49545394
# Posted by francis, modified by community. See post 'Timeline' for change history
# Retrieved 2026-02-21, License - CC BY-SA 4.0

fft_accel_io = fft(norm_accel_io[:, 1])
# print(fft_accel_io) # debugging

def abs2(x):
    return x.real**2 + x.imag**2

fft_accel_io_ampl = abs2(fft_accel_io)
pos_max_accel_io_ampl = np.argmax(fft_accel_io_ampl)

# print(pos_max_accel_io_ampl) # debugging
# print(len(norm_accel_io)) # debugging


# print(fft_accel_io_ampl[pos_max_accel_io_ampl]) # debugging
# print(np.max(fft_accel_io_ampl)) # debugging


freq = fftfreq(number_of_points, d=timestep)
# print(freq.shape) # debugging
# print(freq[pos_max_accel_io_ampl]) # debugging

freq_max_accel_io_ampl = freq[pos_max_accel_io_ampl]
period_max_accel_io_ampl = 1/freq_max_accel_io_ampl
print("The period of the variation of the acceleration is ", period_max_accel_io_ampl, " seconds")








# selfconvol=np.fft.irfft(abs2(fft_accel_io), norm="ortho")
# selfconvol=selfconvol/selfconvol[0]

# # plt.figure()
# # plt.plot(selfconvol)
# # plt.savefig('first.jpg')
# # plt.show()

# print(selfconvol) # debugging

# # let's get a max, assuming a least 4 periods...
# multipleofperiod=np.argmax(selfconvol[1:len(selfconvol)//4])
# norm_accel_io_trunc = norm_accel_io[0:(len(norm_accel_io)//multipleofperiod)*multipleofperiod]

# fft = np.fft.rfft(norm_accel_io_trunc, norm="ortho")
# selfconvol=np.fft.irfft(abs2(fft), norm="ortho")
# selfconvol=selfconvol/selfconvol[0]

# # plt.figure()
# # plt.plot(selfconvol)
# # plt.savefig('second.jpg')
# # plt.show()


# #get ranges for first min, second max
# fmax=np.max(selfconvol[1:len(norm_accel_io_trunc)//4])
# fmin=np.min(selfconvol[1:len(norm_accel_io_trunc)//4])
# xstartmin=1
# while selfconvol[xstartmin]>fmin+0.2*(fmax-fmin) and xstartmin< len(norm_accel_io_trunc)//4:
#     xstartmin=xstartmin+1

# xstartmax=xstartmin
# while selfconvol[xstartmax]<fmin+0.7*(fmax-fmin) and xstartmax< len(norm_accel_io_trunc)//4:
#     xstartmax=xstartmax+1

# xstartmin=xstartmax
# while selfconvol[xstartmin]>fmin+0.2*(fmax-fmin) and xstartmin< len(norm_accel_io_trunc)//4:
#     xstartmin=xstartmin+1

# period=np.argmax(selfconvol[xstartmax:xstartmin])+xstartmax

# print("The period is ",period)
