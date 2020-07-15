/*
 * View model for OctoPrint-TimeToFilament
 *
 * Author: eyal0
 * License: AGPLv3
 */
$(function() {
  function TimeToFilamentViewModel(parameters) {
    var self = this;

    self.settingsViewModel = parameters[0];

    self.onBeforeBinding = function() {
      let settings = self.settingsViewModel.settings;
      let timeToFilamentSettings = settings.plugins.TimeToFilament;
      self.displayLines = timeToFilamentSettings.displayLines;
      self.sampleGcode = ko.observable(
        "; This is a fake gcode file for testing your display lines.\n" +
          "; The first ^ in the file is the pretend current file position, otherwise just the first character.\n" +
          "; You can modify this.\n" +
          "G00 whatever\n" +
          "; layer 1\n" +
          "M12345 more pretend stuff\n" +
          "M600 whatever\n");
      printElement = document.evaluate('//*[@id="state"]/div/span[text() = "Printed"]', document);
      printElement = printElement.iterateNext();
      newDiv = document.createElement("div");
      newDiv.id = "TimeToFilament";
      printElement.parentNode.insertBefore(newDiv, printElement);
    }

    self.resetToDefault = function() {
      OctoPrint.get(OctoPrint.getBlueprintUrl("TimeToFilament") + "get_settings_defaults").done(
        function (defaults) {
          self.displayLines(ko.mapping.fromJS(defaults["displayLines"])());
        });
    }

    self.addLine = function() {
      self.displayLines.push({description: "", regex: "", format: "", enabled: true});
    }

    self.removeLine = function(line) {
      self.displayLines.remove(line);
    }

    self.sampleOutput = ko.pureComputed(function() {
      progress = {}
      progress.filepos = Math.max(0, self.sampleGcode().indexOf("^"));
      progress.printTime = 0;
      progress.printTimeLeft = 0;
      for (let c of self.sampleGcode()) {
        if (progress.printTimeLeft == 0 && c != "^") {
          progress.printTime += c.charCodeAt(0);
        } else {
          progress.printTimeLeft += c.charCodeAt(0);
        }
      }
      progress.completion = progress.filepos / self.sampleGcode().length;
      progress.TimeToFilament = {};
      for (const displayLine of self.displayLines()) {
        const regex = displayLine.regex();
        const format = displayLine.format();
        let posSoFar = 0;
        let timeSoFar = 0;
        for (let line of self.sampleGcode().substr(progress.filepos).split("\n")) {
          if (m = line.match(regex)) {
            progress.TimeToFilament[regex] = {
              "group": m[0],
              "groupdict": m.groups,
              "groups": m.slice(1),
              "matchPos": posSoFar,
              "searchPos": progress.filepos,
              "timeLeft": progress.printTimeLeft - timeSoFar,
            };
          }
          posSoFar += line.length;
          timeSoFar += [...line].reduce((a,b) => a+b.charCodeAt(0), 0);
        }
      }
      return {"progress": progress};
    });

    self.sampleFormatOutput = function(displayLineIndex) {
      if (!(self.displayLines()[displayLineIndex()].regex() in self.sampleOutput()["progress"]["TimeToFilament"])) {
        return "'" + self.displayLines()[displayLineIndex()].regex() + "' not found in this.progress.TimeToFilament";
      }
      try {
        const fillTemplate = function(templateString, templateVars){
          return new Function(`return \`${templateString}\`;`).call(templateVars);
        }
        return fillTemplate(self.displayLines()[displayLineIndex()].format(), self.sampleOutput());
      } catch(e) {
        return "Threw exception: " + e.message;
      }
    }

    self.fromCurrentData = function(data) {
      if (!("progress" in data) || !("TimeToFilament" in data["progress"])) {
        let div = document.getElementById("TimeToFilament");
        if (div) {
          div.style.display = "none";
        }
        return;
      }
      document.getElementById("TimeToFilament").style.display = "";
      const displayLines = self.displayLines();
      for (const displayLine of displayLines) {
        const regex = displayLine.regex();
        if (regex in data["progress"]["TimeToFilament"]) {
          let found = document.getElementById("TimeToFilament-" + regex);
          if (!found) {
            let newLine = document.createElement("span");
            newLine.id = "TimeToFilament-" + regex;
            newLine.style = "display: block;";
            document.getElementById("TimeToFilament").appendChild(newLine);
          }
          // Back to default which is probably to show it.
          document.getElementById("TimeToFilament").style.display = "";
          result = data["progress"]["TimeToFilament"][regex];
          const fillTemplate = function(templateString, templateVars){
            return new Function(`return \`${templateString}\`;`).call(templateVars);
          }
          document.getElementById("TimeToFilament-" + regex).innerHTML = fillTemplate(displayLine.format(), data);
        } else {
          let found = document.getElementById("TimeToFilament-" + regex);
          if (found) {
            document.getElementById("TimeToFilament-" + regex).style.display = "none";
          }
        }
      }
    }
  }
  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */
  OCTOPRINT_VIEWMODELS.push({
    construct: TimeToFilamentViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: [ "settingsViewModel" ],
    // Elements to bind to, e.g. #settings_plugin_TimeToFilament, #tab_plugin_TimeToFilament, ...
    elements: [ "#settings_plugin_TimeToFilament" ]
  });
});
