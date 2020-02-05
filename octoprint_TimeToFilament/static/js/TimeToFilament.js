/*
 * View model for OctoPrint-TimeToFilament
 *
 * Author: eyal0
 * License: AGPLv3
 */
$(function() {
  function TimetofilamentViewModel(parameters) {
    var self = this;

    self.settingsViewModel = parameters[0];

    self.onBeforeBinding = function() {
      printElement = document.evaluate('//*[@id="state"]/div/span[text() = "Printed"]', document);
      printElement = printElement.iterateNext();
      newDiv = document.createElement("div");
      newDiv.id = "TimeToFilament";
      printElement.parentNode.insertBefore(newDiv, printElement);
    }

    self.fromCurrentData = function(data) {
      console.log(data);
      if (!("progress" in data) || !("TimeToFilament" in data["progress"])) {
        console.log("get rid of it!!!");
        let div = document.getElementById("TimeToFilament");
        if (div) {
          div.style.display = "none";
        }
        return;
      }
      document.getElementById("TimeToFilament").style.display = "";
      const displayLines = self.settingsViewModel.settings.plugins.TimeToFilament.displayLines();
      for (const displayLine of displayLines) {
        const regex = displayLine.regex();
        console.log(regex);
        if (regex in data["progress"]["TimeToFilament"]) {
          let found = document.getElementById("TimeToFilament-" + regex);
          if (!found) {
            let newLine = document.createElement("span");
            newLine.id = "TimeToFilament-" + regex;
            document.getElementById("TimeToFilament").appendChild(newLine);
          }
          // Back to default which is probably to show it.
          document.getElementById("TimeToFilament").style.display = "";
          result = data["progress"]["TimeToFilament"][regex];
          console.log(result);
          console.log("foo " + displayLine.format());
          const fillTemplate = function(templateString, templateVars){
            return new Function(`return \`${templateString}\`;`).call(templateVars);
          }
          document.getElementById("TimeToFilament-" + regex).innerHTML = fillTemplate(displayLine.format(), data);
        } else {
          let found = document.getElementById("TimeToFilament-" + regex);
          if (found) {
            document.getElementById("TimeToFilament").style.display = "none";
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
    construct: TimetofilamentViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: [ "settingsViewModel" ],
    // Elements to bind to, e.g. #settings_plugin_TimeToFilament, #tab_plugin_TimeToFilament, ...
    elements: [ /* ... */ ]
  });
});
