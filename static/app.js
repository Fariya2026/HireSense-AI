document.addEventListener("DOMContentLoaded", () => {
  const salarySlider = document.querySelector('input[name="salary_min"]');
  const salaryLabel = document.getElementById("salary-min-label");

  if (salarySlider && salaryLabel) {
    const updateSalary = () => {
      salaryLabel.textContent = `$${Number(salarySlider.value).toLocaleString()}`;
    };
    salarySlider.addEventListener("input", updateSalary);
    updateSalary();
  }

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.matches(".application-form")) {
        const submitButton = form.querySelector('button[type="submit"]');
        const skills = form.querySelector('input[name="skills"]');
        const fileInput = form.querySelector('input[name="resume_file"]');
        const resumeText = form.querySelector('textarea[name="resume_text"]');
        const validation = form.querySelector("[data-resume-validation]");
        if (submitButton.disabled || form.dataset.prepared !== "true") {
          event.preventDefault();
          validation.textContent = "Match your skills and review the prepared note before submitting.";
          skills.focus();
          return;
        }
        if (!fileInput.files.length && !resumeText.value.trim()) {
          event.preventDefault();
          validation.textContent = "Upload a resume file or paste your resume text to continue.";
          resumeText.focus();
          return;
        }
        validation.textContent = "";
      }
      const button = form.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;
      button.disabled = true;
      button.classList.add("is-loading");
      button.replaceChildren();
      const spinner = document.createElement("span");
      spinner.className = "loading-spinner";
      spinner.setAttribute("aria-hidden", "true");
      button.append(spinner, document.createTextNode(" Please wait…"));
    });
  });

  const applicationForm = document.querySelector(".application-form");
  const prepareButton = applicationForm?.querySelector("[data-prepare-application]");
  if (applicationForm && prepareButton) {
    const skillsInput = applicationForm.querySelector('input[name="skills"]');
    const nameInput = applicationForm.querySelector('input[name="name"]');
    const submitButton = applicationForm.querySelector('button[type="submit"]');
    const validation = applicationForm.querySelector("[data-resume-validation]");
    const matchResults = applicationForm.querySelector("[data-match-results]");
    const applicationNote = applicationForm.querySelector('textarea[name="application_note"]');
    const invalidatePreparation = () => {
      applicationForm.dataset.prepared = "false";
      submitButton.disabled = true;
      submitButton.textContent = "Prepare match to continue →";
      matchResults.hidden = true;
    };
    [skillsInput, nameInput].forEach((input) => input.addEventListener("input", invalidatePreparation));

    prepareButton.addEventListener("click", async () => {
      const skills = skillsInput.value.trim();
      if (!skills) {
        validation.textContent = "Enter the skills you want matched to this role.";
        skillsInput.focus();
        return;
      }

      validation.textContent = "";
      const requestedName = nameInput.value.trim();
      prepareButton.disabled = true;
      prepareButton.classList.add("is-loading");
      prepareButton.textContent = "Matching skills…";
      try {
        const response = await fetch(prepareButton.dataset.prepareUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: requestedName, skills }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Could not prepare this application.");
        if (skillsInput.value.trim() !== skills || nameInput.value.trim() !== requestedName) {
          throw new Error("Your details changed while matching. Prepare the draft again.");
        }

        const percent = Math.max(0, Math.min(100, Number(result.match_percent) || 0));
        matchResults.querySelector("[data-match-percent]").textContent = String(percent);
        matchResults.querySelector("[data-match-bar]").style.width = `${percent}%`;
        matchResults.querySelector("[data-match-summary]").textContent = result.matched.length
          ? `Matching skills: ${result.matched.join(", ")}.`
          : "No listed role skills matched yet. Review the gaps before deciding whether to apply.";
        matchResults.querySelector("[data-match-missing]").textContent = result.missing.length
          ? `Skills to build: ${result.missing.join(", ")}.`
          : "All listed role skills are represented in your self-reported skills.";
        applicationNote.value = result.application_note;
        matchResults.hidden = false;
        applicationForm.dataset.prepared = "true";
        submitButton.disabled = false;
        submitButton.textContent = "Submit application →";
        window.HireSenseToast?.show("Skills matched. Review your application note before submitting.", "success");
      } catch (error) {
        validation.textContent = error.message;
      } finally {
        prepareButton.disabled = false;
        prepareButton.classList.remove("is-loading");
        prepareButton.textContent = "Match skills & prepare draft";
      }
    });
  }

  document.querySelectorAll("[data-job-href]").forEach((card) => {
    const navigate = () => window.location.assign(card.dataset.jobHref);
    card.addEventListener("click", (event) => {
      if (event.target.closest("a, button, details, summary, form, input, select, textarea")) return;
      navigate();
    });
    card.addEventListener("keydown", (event) => {
      if (event.target !== card || !["Enter", " "].includes(event.key)) return;
      event.preventDefault();
      navigate();
    });
  });

  const dialog = document.getElementById("application-dialog");
  document.querySelectorAll("[data-open-application]").forEach((button) => {
    button.addEventListener("click", () => {
      if (dialog?.showModal) dialog.showModal();
      else document.querySelector(".application-form")?.scrollIntoView({ behavior: "smooth" });
    });
  });
  document.querySelectorAll("[data-close-application]").forEach((button) => {
    button.addEventListener("click", () => dialog?.close());
  });
  dialog?.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  document.querySelectorAll("[data-toast-type]").forEach((message) => {
    window.HireSenseToast?.show(message.textContent.trim(), message.dataset.toastType);
  });
  document.querySelector(".flash-stack")?.remove();
});
