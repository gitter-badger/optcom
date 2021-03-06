from optcom import *

domain = Domain(samples_per_bit=512, bit_width=2.0)

lt = Layout(domain)
pulse = Gaussian(channels=1, peak_power=[5.0], width=[0.2],
                 center_lambda=[1550.0])

alpha = 0.046
steps = int(1e1)
x_datas = []
y_datas = []

fiber = Fiber(length=5.0, method="ssfm", alpha=alpha,
              nl_approx=True, ATT=True, DISP=False, SPM=False, SS=False,
              RS=False, steps=steps, medium='sio2', save=True)

lt.link((pulse[0], fiber[0]))
lt.run(pulse)
x_datas.append(pulse[0][0].time)
x_datas.append(fiber[0][0].time)
y_datas.append(temporal_power(pulse[0][0].channels))
y_datas.append(temporal_power(fiber[1][0].channels))
x_datas.append(pulse[0][0].nu)
x_datas.append(fiber[0][0].nu)
y_datas.append(spectral_power(pulse[0][0].channels))
y_datas.append(spectral_power(fiber[1][0].channels))
x_datas.append(pulse[0][0].time)
x_datas.append(fiber[1][0].time)
y_datas.append(phase(pulse[0][0].channels))
y_datas.append(phase(fiber[1][0].channels))

x_labels = ['t', 'nu', 't']
y_labels = ['P_t', 'P_nu', 'phi']
plot_titles = ["Temporal power", "Spectral power", "Phase"]
fig_title = "Effect of attenuation on Gaussian pulse"

plot_groups = [0,0,1,1,2,2]
plot_labels = 3 * ['original pulse', 'w/ attenuation']
x_ranges = [None, (182., 205.), None]


plot2d(x_datas, y_datas, x_labels=x_labels, y_labels=y_labels,
       x_ranges=x_ranges, plot_titles=plot_titles, plot_groups=plot_groups,
       plot_labels=plot_labels, fig_title=fig_title, opacity=0.1,
       triangle_layout=True,
       filename="./examples/fiber_effects/images/att_effect.png")
