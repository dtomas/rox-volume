import gtk

import rox
from rox import OptionsBox, Menu
from rox.options import Option

try:
	import alsaaudio
except:
	rox.croak(_("You need to install the pyalsaaudio module"))


APP_NAME = 'Volume'


#Options.xml processing
rox.setup_app_options(APP_NAME, site='hayber.us')
Menu.set_save_name(APP_NAME, site='hayber.us')

SHOW_ICON = Option('show_icon', True)
SHOW_BAR = Option('show_bar', False)
THEME = Option('theme', 'gtk-theme')

volume_control = None
mixer_device_name = None
for card_index, card in enumerate(alsaaudio.cards()):
	for channel in alsaaudio.mixers(card_index):
		try:
			mixer = alsaaudio.Mixer(channel, 0, card_index)
		except alsaaudio.ALSAAudioError:
			continue
		if len(mixer.volumecap()):
			if volume_control is None:
				volume_control = channel
			if mixer_device_name is None:
				mixer_device_name = card

if volume_control is None:
	volume_control = 'Master'
if mixer_device_name is None:
	mixer_device_name = 'default'

VOLUME_CONTROL = Option('mixer_channels', volume_control)
MIXER_DEVICE = Option('mixer_device', mixer_device_name)

# Mixer options
SHOW_VALUES = Option('show_values', False)
SHOW_CONTROLS = Option('controls', -1)

MASK_LOCK = Option('lock_mask', -1)
MASK_MUTE = Option('mute_mask', 0)


def build_mixer_devices_list(box, node, label, option):
	hbox = gtk.HBox(False, 4)
	hbox.pack_start(box.make_sized_label(label), False, True, 0)

	button = gtk.OptionMenu()
	hbox.pack_start(button, True, True, 0)

	menu = gtk.Menu()
	button.set_menu(menu)

	for card_index, name in enumerate(alsaaudio.cards()):
		show_card = False
		for channel in alsaaudio.mixers(card_index):
			try:
				mixer = alsaaudio.Mixer(channel, 0, card_index)
			except alsaaudio.ALSAAudioError:
				continue
			if len(mixer.volumecap()):
				show_card = True
				break
		if show_card:
			item = gtk.MenuItem(name)
			menu.append(item)
			item.show_all()

	def update_mixer_device():
		i = -1
		for kid in menu.get_children():
			i += 1
			item = kid.child
			if not item:
				item = button.child
			label = item.get_text()
			if label == option.value:
				button.set_history(i)

	def read_mixer_device(): return button.child.get_text()
	box.handlers[option] = (read_mixer_device, update_mixer_device)
	button.connect('changed', lambda w: box.check_widget(option))
	return [hbox]
OptionsBox.widget_registry['mixer_devices_list'] = build_mixer_devices_list


def get_mixer_device():
    try:
	    return alsaaudio.cards().index(MIXER_DEVICE.value)
    except ValueError:
	    return 0


def build_channel_list(box, node, label, option):
	hbox = gtk.HBox(False, 4)

	hbox.pack_start(box.make_sized_label(label), False, True, 0)

	button = gtk.OptionMenu()
	hbox.pack_start(button, True, True, 0)

	def build():

		menu = gtk.Menu()
		button.set_menu(menu)
		mixer_device = get_mixer_device()
		for channel in alsaaudio.mixers(mixer_device):
			try:
				mixer = alsaaudio.Mixer(channel, 0, mixer_device)
			except alsaaudio.ALSAAudioError:
				continue
			if len(mixer.volumecap()):
				item = gtk.MenuItem(channel)
				menu.append(item)
				item.show_all()
		button.set_history(0)
		return menu

	class state:
		menu = build()

	def update_channel():
		i = -1
		for kid in state.menu.get_children():
			i += 1
			item = kid.child
			if not item:
				item = button.child
			label = item.get_text()
			if label == option.value:
				button.set_history(i)

	def read_channel():
	    if button.child is None:
		return ''
	    return button.child.get_text()
	box.handlers[option] = (read_channel, update_channel)
	button.connect('changed', lambda w: box.check_widget(option))

	def options_changed():
		if MIXER_DEVICE.has_changed:
			state.menu = build()
			box.check_widget(option)
	box.options.add_notify(options_changed)
	return [hbox]
OptionsBox.widget_registry['channel_list'] = build_channel_list

rox.app_options.notify()
