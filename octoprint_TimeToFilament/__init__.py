# coding=utf-8
from __future__ import absolute_import

import types
import re
import logging
import octoprint.plugin

class TimeToFilamentPlugin(octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.StartupPlugin):

  ##~~ SettingsPlugin mixin
  def get_settings_defaults(self):
    return {
        "displayLines": [
            {"enabled": true,
             "description": "Time to Next Filament Change",
             "regex": "^M600",
             "format": "Filament Change in {secondsUntil} seconds"}
        ]
    }

  ##~~ StartupPlugin API
  def on_startup(self, host, port):
    def newUpdateProgressDataCallback(old_callback, printer):
      def return_function(self):
        old_result = dict(old_callback())
        try:
          print(printer._comm._currentFile.getFilename())
          with open(printer._comm._currentFile.getFilename()) as gcode_file:
            gcode_file.seek(printer._comm._currentFile.getFilepos())
            # Now search forward for the regex.
            regexes = set(x["regex"]
                          for x in self._settings["displayLines"]
                          if x["enabled"])
            while regexes:
              line = gcode_file.readline()
              print(line)
              for regex in list(regexes): # Make a copy because we modify it.
                m = re.match(regex, line)
                print(m)
                if m:
                  match_pos = gcode_file.tell()
                  timeLeft, timeOrigin = printer._estimator.estimate(
                      float(match_pos) / printer._comm._currentFile.getFilesize(),
                      None, None, None, None)
                  print(printer._estimator)
                  print(timeLeft)
                  print(timeOrigin)
                  if not "TimeToFilament" in old_result:
                    old_result["TimeToFilament"] = dict()
                  old_result["TimeToFilament"][regex] = {
                      "timeLeft": timeLeft,
                      "match": m
                  }
                  regexes.remove(regex)
        except Exception as e:
          print(e)
        finally:
          return old_result
      return return_function
    self._printer._stateMonitor._on_get_progress = types.MethodType(newUpdateProgressDataCallback(
        self._printer._stateMonitor._on_get_progress, self._printer), self._printer._stateMonitor)


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
