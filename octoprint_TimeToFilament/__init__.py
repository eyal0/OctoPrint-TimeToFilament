# coding=utf-8
from __future__ import absolute_import

import copy
import types
import re
import octoprint.plugin
import json
import logging
import time
from collections import defaultdict

dd = lambda: defaultdict(dd)


class TimeToFilamentPlugin(octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.StartupPlugin,
                           octoprint.plugin.BlueprintPlugin):

  def __init__(self):
    self._logger = logging.getLogger(__name__)
    self._last_debug = 0
    self._cached_currentFile = None
    self._cached_results = dd()

  ##~~ SettingsPlugin mixin
  def get_settings_defaults(self):
    return {
        "displayLines": [
            {"enabled": True,
             "description": "Time to Next Layer",
             "regex": "^; layer (\\d+)",
             "format": 'Layer ${this.plugins.TimeToFilament["^; layer (\\\\d+)"].groups[0]} in <b>${formatDuration(this.progress.printTimeLeft - this.plugins.TimeToFilament["^; layer (\\\\d+)"].timeLeft)}</b>'},
            {"enabled": True,
             "description": "Time to Next Filament Change",
             "regex": "^M600",
             "format": 'Filament change in <b>${formatDuration(this.progress.printTimeLeft - this.plugins.TimeToFilament["^M600"].timeLeft)}</b>'},
            {"enabled": False,
             "description": "Time of Next Filament Change",
             "regex": "^M600",
             "format": 'Filament change at <b>${new Date(Date.now() + (this.progress.printTimeLeft - this.plugins.TimeToFilament["^M600"].timeLeft)*1000).toLocaleTimeString([], {hour12:false})}</b>'},
            {"enabled": True,
             "description": "Time to Next Next Pause",
             "regex": "^M601",
             "format": 'Next pause in <b>${formatDuration(this.progress.printTimeLeft - this.plugins.TimeToFilament["^M601"].timeLeft)}</b>'},
            {"enabled": False,
             "description": "Time of Next Next Pause",
             "regex": "^M601",
             "format": 'Next pause at <b>${new Date(Date.now() + (this.progress.printTimeLeft - this.plugins.TimeToFilament["^M601"].timeLeft)*1000).toLocaleTimeString([], {hour12:false})}</b>'},
        ]
    }

  ##~~ StartupPlugin API
  def on_startup(self, host, port):
     # setup our custom logger
    from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
    logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="engine"), when="D", backupCount=3)
    logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logging_handler.setLevel(logging.DEBUG)

    self._logger.addHandler(logging_handler)
    self._logger.propagate = False

  @octoprint.plugin.BlueprintPlugin.route("/get_settings_defaults", methods=["GET"])
  def get_settings_defaults_as_string(self):
    return json.dumps(self.get_settings_defaults())

  ##~~ AssetPlugin mixin
  def get_assets(self):
    # Define your plugin's asset files to automatically include in the
    # core UI here.
    return dict(
        js=["js/TimeToFilament.js"],
        css=["css/TimeToFilament.css"],
        less=["less/TimeToFilament.less"]
    )

  ##~~ Softwareupdate hook

  def get_update_information(self):
    # Define the configuration for your plugin to use with the Software Update
    # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
    # for details.
    return dict(
        TimeToFilament=dict(
            displayName="TimeToFilament Plugin",
            displayVersion=self._plugin_version,

            # version check: github repository
            type="github_release",
            user="eyal0",
            repo="OctoPrint-TimeToFilament",
            current=self._plugin_version,

            # update method: pip
            pip="https://github.com/eyal0/OctoPrint-TimeToFilament/archive/{target_version}.zip"
        )
    )

  def additional_state_data(self, initial, *args, **kwargs):
    try:
      if not hasattr(self, "_printer"):
        # The printer object wasn't yet loaded.
        return None
      if not self._printer._comm._currentFile:
        return None
      # Can we use the cached result?
      if self._printer._comm._currentFile is not self._cached_currentFile:
        # No, we need to clear out the cache.
        self._cached_results = dd()
        self._cached_currentFile = self._printer._comm._currentFile
      file_pos = self._cached_currentFile.getFilepos()
      for regex, cached_result in list(self._cached_results.items()):
        if (file_pos > cached_result["matchPos"] or
            file_pos < cached_result["searchPos"]):
          del self._cached_results[regex]
      regexes = set(x["regex"]
                    for x in self._settings.get(["displayLines"])
                    if x["enabled"] and (x["regex"] not in self._cached_results.keys()))
      if regexes:
        with open(self._cached_currentFile.getFilename()) as gcode_file:
          gcode_file.seek(file_pos)
          # Now search forward for the regex.
          while regexes:
            line = gcode_file.readline()
            if not line:
              # Ran out of lines and didn't find anything more.
              for regex in list(regexes):
                self._cached_results[regex]["matchPos"] = float("inf")
                self._cached_results[regex]["searchPos"] = file_pos
              break
            for regex in list(regexes): # Make a copy because we modify it.
              m = re.search(regex, line)
              if m:
                match_pos = gcode_file.tell()
                time_left, _ = self._printer._estimator.estimate(
                    float(match_pos) / self._cached_currentFile.getFilesize(),
                    None, None, None, None)
                self._cached_results[regex] = {
                    "timeLeft": time_left,
                    "groups": m.groups(),
                    "group": m.group(),
                    "groupdict": m.groupdict(),
                    "matchPos": match_pos,
                    "searchPos": file_pos,
                }
                regexes.remove(regex)
      ret = copy.deepcopy(self._cached_results)
      for regex in list(ret.keys()): # Make a copy because we will modify ret
        if ret[regex]["matchPos"] == float("inf"):
          del ret[regex]
      if (time.time() > self._last_debug + 10):
        self._logger.info("sending: %s", json.dumps(ret))
        self._last_debug = time.time()
      return ret
    except Exception as e:
      self._logger.error("Failed: %s", repr(e))
    return None

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "TimeToFilament Plugin"

__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
  global __plugin_implementation__
  __plugin_implementation__ = TimeToFilamentPlugin()

  global __plugin_hooks__
  __plugin_hooks__ = {
      "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
      "octoprint.printer.additional_state_data": __plugin_implementation__.additional_state_data
  }
