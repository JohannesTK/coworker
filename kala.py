from Cocoa import NSDictionary
from Quartz import kAXTrustedCheckOptionPrompt, AXIsProcessTrustedWithOptions

opts = NSDictionary.dictionaryWithDictionary_({kAXTrustedCheckOptionPrompt: True})
AXIsProcessTrustedWithOptions(opts)  # Triggers the OS prompt if not granted
