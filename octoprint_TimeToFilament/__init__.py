# coding=utf-8
from __future__ import absolute_import

import types
import re
import logging
import octoprint.plugin
import json
from collections import defaultdict

dd = lambda: defaultdict(dd)

class TimeToFilamentPlugin(octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.StartupPlugin,
                           octoprint.plugin.BlueprintPlugin):

  def __init__(self):
    self._cached_currentFile = None
    self._cached_results = dd()

  ##~~ SettingsPlugin mixin
  def get_settings_defaults(self):
    return {
        "displayLines": [
            {"enabled": True,
             "description": "Time to Next Layer",
             "regex": "^; layer (\\d+)",
             "format": 'Layer ${this.progress.TimeToFilament["^; layer (\\\\d+)"].groups[0]} in <b>${Math.round(this.progress.printTimeLeft - this.progress.TimeToFilament["^; layer (\\\\d+)"].timeLeft)} seconds</b>'},
            {"enabled": True,
             "description": "Time to Next Filament Change",
             "regex": "^M600",
             "format": 'Filament change in <b>${Math.round(this.progress.printTimeLeft - this.progress.TimeToFilament["^M600"].timeLeft)} seconds</b>'}
        ]
    }

  ##~~ StartupPlugin API
  def on_startup(self, host, port):
    def newUpdateProgressDataCallback(old_callback, printer):
      def return_function(state_monitor):
        old_result = dd()
        # Get the results from the original callback, to be updated.
        old_result.update(old_callback())
        try:
          # Can we use the cached result?
          if printer._comm._currentFile is not self._cached_currentFile:
            # No, we need to clear out the cache.
            self._cached_results = dd()
            self._cached_currentFile = printer._comm._currentFile
          file_pos = printer._comm._currentFile.getFilepos()
          for regex, cached_result in list(self._cached_results.items()):
            if (file_pos > cached_result["matchPos"] or
                file_pos < cached_result["searchPos"]):
              del self._cached_results[regex]
          old_result["TimeToFilament"].update(self._cached_results)
          regexes = set(x["regex"]
                        for x in self._settings.get(["displayLines"])
                        if x["enabled"] and (x["regex"] not in old_result["TimeToFilament"].keys()))
          if regexes:
            with open(printer._comm._currentFile.getFilename()) as gcode_file:
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
                    timeLeft, timeOrigin = printer._estimator.estimate(
                        float(match_pos) / printer._comm._currentFile.getFilesize(),
                        None, None, None, None)
                    self._cached_results[regex] = {
                        "timeLeft": timeLeft,
                        "groups": m.groups(),
                        "group": m.group(),
                        "groupdict": m.groupdict(),
                        "matchPos": match_pos,
                        "searchPos": file_pos,
                    }
                    regexes.remove(regex)
          old_result["TimeToFilament"].update(self._cached_results)
        except Exception as e:
          print("Failed: " + repr(e))
        for regex in list(old_result["TimeToFilament"].keys()):
          if old_result["TimeToFilament"][regex]["matchPos"] == float("inf"):
            del old_result["TimeToFilament"][regex]
        return old_result
      return return_function
    self._printer._stateMonitor._on_get_progress = types.MethodType(newUpdateProgressDataCallback(
        self._printer._stateMonitor._on_get_progress, self._printer), self._printer._stateMonitor)

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
      "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
  }
