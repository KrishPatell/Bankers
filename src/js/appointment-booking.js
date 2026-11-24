/* Appointment form behaviour for contact-us.html and the two public booking
 * aliases. The form stays on the existing /api/contact lead path; this script
 * only manages configurable city schedules, route preselection and validation.
 */
(function () {
  "use strict";

  var form = document.querySelector("form[data-appointment-form]");
  if (!form) return;

  var citySelect = form.querySelector("[data-appointment-city]");
  var diseaseSelect = form.querySelector("[data-appointment-disease]");
  var dateInput = form.querySelector("[data-appointment-date]");
  var timeSelect = form.querySelector("[data-appointment-time]");
  var callbackInput = form.querySelector("[data-appointment-callback]");
  var consentInput = form.querySelector("[data-appointment-consent]");
  var otherCityWrap = form.querySelector("[data-other-city-wrap]");
  var otherCityInput = form.querySelector("[data-appointment-other-city]");
  var status = form.querySelector("[data-appointment-status]");
  if (!citySelect || !diseaseSelect || !dateInput || !timeSelect || !callbackInput || !consentInput) return;

  var availableDates = [];
  var diseaseValues = [];
  var today = indiaDateString(new Date());
  var routeCity = cityFromUrl();
  var fallbackConfig = {
    cities: Array.prototype.map.call(citySelect.options, function (option) {
      return { name: option.value, active: Boolean(option.value) };
    }).filter(function (item) { return item.name; }),
    diseases: initialDiseaseValues(),
    schedules: {}
  };

  function indiaDateString(date) {
    var parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).formatToParts(date).reduce(function (result, part) {
      if (part.type !== "literal") result[part.type] = part.value;
      return result;
    }, {});
    var year = parts.year;
    var month = parts.month;
    var day = parts.day;
    return year + "-" + month + "-" + day;
  }

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function cityFromUrl() {
    var queryCity = "";
    try {
      queryCity = new URLSearchParams(window.location.search).get("city") || "";
    } catch (_) {}
    var pathMatch = window.location.pathname.match(/\/book-appointment\/([^/]+)\/?$/i);
    var pathCity = "";
    if (pathMatch) {
      try { pathCity = decodeURIComponent(pathMatch[1]); } catch (_) { pathCity = pathMatch[1]; }
      pathCity = pathCity.replace(/[-_]+/g, " ");
    }
    var value = queryCity || pathCity;
    if (!value) return "";
    return value.replace(/\b\w/g, function (letter) { return letter.toUpperCase(); });
  }

  function option(select, value, label, disabled) {
    var item = document.createElement("option");
    item.value = value;
    item.textContent = label;
    if (disabled) item.disabled = true;
    select.appendChild(item);
  }

  function initialDiseaseValues() {
    var source = diseaseSelect;
    if (diseaseSelect.tagName.toLowerCase() === "input") {
      var listId = diseaseSelect.getAttribute("list");
      source = listId ? document.getElementById(listId) : null;
    }
    return source ? Array.prototype.map.call(source.options || [], function (item) {
      return item.value;
    }).filter(Boolean) : [];
  }

  function scopedCityNames(items) {
    var scope = String(form.getAttribute("data-appointment-city-scope") || "").trim();
    var allowed = scope ? scope.split("|").map(normalize) : null;
    return (items || []).filter(function (item) {
      return typeof item === "string" || item.active !== false;
    }).map(function (item) {
      return typeof item === "string" ? item : item.name;
    }).filter(function (city) {
      return city && (!allowed || allowed.indexOf(normalize(city)) >= 0);
    });
  }

  function renderCities(items, selected) {
    var active = scopedCityNames(items);
    if (!active.length) return;
    citySelect.innerHTML = "";
    option(citySelect, "", "Select your city", true);
    active.forEach(function (city) { option(citySelect, city, city, false); });
    citySelect.value = active.some(function (city) { return normalize(city) === normalize(selected); }) ? selected : "";
  }

  function renderDiseases(items, selected) {
    var diseases = (items || []).filter(Boolean);
    if (!diseases.length) return;
    diseaseValues = diseases;
    if (diseaseSelect.tagName.toLowerCase() === "input") {
      var listId = diseaseSelect.getAttribute("list");
      var list = listId ? document.getElementById(listId) : null;
      if (list) {
        list.innerHTML = "";
        diseases.forEach(function (disease) { option(list, disease, disease, false); });
      }
      diseaseSelect.value = diseases.indexOf(selected) >= 0 ? selected : "";
      return;
    }
    diseaseSelect.innerHTML = "";
    option(diseaseSelect, "", "Select a disease or condition", true);
    diseases.forEach(function (disease) { option(diseaseSelect, disease, disease, false); });
    diseaseSelect.value = diseases.indexOf(selected) >= 0 ? selected : "";
  }

  function scheduleFor(config, city) {
    var schedules = config && config.schedules ? config.schedules : {};
    return schedules[city] || { dates: [], timings: [], note: "" };
  }

  function validFutureDates(schedule) {
    return (schedule.dates || []).filter(function (value) {
      return /^\d{4}-\d{2}-\d{2}$/.test(String(value)) && String(value) >= today;
    }).sort();
  }

  function formatDate(value) {
    var parts = String(value).split("-");
    if (parts.length !== 3) return value;
    var date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  }

  function updateTimeOptions(schedule) {
    var timings = (schedule.timings || []).filter(Boolean);
    timeSelect.innerHTML = "";
    option(timeSelect, "", timings.length ? "Select a preferred time" : "Timing will be confirmed by hospital team", false);
    timings.forEach(function (timing) { option(timeSelect, timing, timing, false); });
    timeSelect.value = "";
  }

  function setStatus(message) {
    if (status) status.textContent = message;
  }

  function updateOtherCity() {
    var isOther = normalize(citySelect.value) === "other city";
    if (otherCityWrap) otherCityWrap.hidden = !isOther;
    if (otherCityInput) {
      otherCityInput.disabled = !isOther;
      otherCityInput.required = isOther;
      if (!isOther) {
        otherCityInput.value = "";
        otherCityInput.setCustomValidity("");
      }
    }
  }

  function validateDisease() {
    if (diseaseSelect.tagName.toLowerCase() !== "input") return;
    var value = String(diseaseSelect.value || "").trim();
    var valid = diseaseValues.some(function (disease) {
      return normalize(disease) === normalize(value);
    });
    diseaseSelect.setCustomValidity(value && !valid
      ? "Please select a condition from the list."
      : "");
  }

  function updateSchedule(config) {
    var city = citySelect.value;
    var schedule = scheduleFor(config, city);
    var dates = validFutureDates(schedule);
    availableDates = dates;
    dateInput.value = "";
    dateInput.min = today;
    dateInput.setCustomValidity("");
    callbackInput.setCustomValidity("");
    updateTimeOptions(schedule);

    if (!city) {
      dateInput.disabled = true;
      dateInput.required = false;
      callbackInput.required = false;
      setStatus("Select a city to see currently configured consultation dates.");
      return;
    }

    if (dates.length) {
      dateInput.disabled = false;
      dateInput.required = true;
      callbackInput.required = false;
      setStatus("Available consultation dates: " + dates.map(formatDate).join(", ") + ". Timing will be confirmed by the hospital team.");
    } else {
      dateInput.disabled = true;
      dateInput.required = false;
      callbackInput.required = true;
      setStatus(schedule.note || "No consultation date is currently published for this city. Select callback request and our hospital team will help.");
    }
  }

  function validateDate() {
    if (dateInput.disabled || !dateInput.value) {
      dateInput.setCustomValidity("");
      return;
    }
    if (dateInput.value < today) {
      dateInput.setCustomValidity("Please choose today or a future date.");
    } else if (availableDates.length && availableDates.indexOf(dateInput.value) === -1) {
      dateInput.setCustomValidity("Please select one of the currently published consultation dates.");
    } else {
      dateInput.setCustomValidity("");
    }
  }

  function validateAppointment() {
    validateDate();
    validateDisease();
    updateOtherCity();
    if (dateInput.disabled && !callbackInput.checked) {
      callbackInput.setCustomValidity("Please request a callback because no consultation date is currently published.");
    } else {
      callbackInput.setCustomValidity("");
    }
    if (!form.checkValidity()) {
      if (typeof form.reportValidity === "function") form.reportValidity();
      return false;
    }
    return true;
  }

  form.__validateAppointment = validateAppointment;
  form.__appointmentConfig = fallbackConfig;
  dateInput.min = today;
  dateInput.disabled = true;
  dateInput.required = false;

  citySelect.addEventListener("change", function () { updateSchedule(form.__appointmentConfig); });
  citySelect.addEventListener("change", updateOtherCity);
  dateInput.addEventListener("change", validateDate);
  diseaseSelect.addEventListener("change", validateDisease);
  diseaseSelect.addEventListener("input", validateDisease);
  callbackInput.addEventListener("change", function () { callbackInput.setCustomValidity(""); });
  if (otherCityInput) otherCityInput.addEventListener("input", function () {
    otherCityInput.setCustomValidity("");
  });

  renderCities(fallbackConfig.cities, routeCity);
  renderDiseases(fallbackConfig.diseases, diseaseSelect.value);
  updateOtherCity();
  updateSchedule(fallbackConfig);

  fetch("/data/appointment-config.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("Appointment config unavailable");
      return response.json();
    })
    .then(function (config) {
      var selectedCity = citySelect.value || routeCity;
      var selectedDisease = diseaseSelect.value;
      form.__appointmentConfig = config;
      renderCities(config.cities, selectedCity);
      renderDiseases(config.diseases, selectedDisease);
      updateOtherCity();
      updateSchedule(config);
    })
    .catch(function () {
      /* The HTML keeps the complete city/disease list as a no-JS fallback. */
    });
}());
