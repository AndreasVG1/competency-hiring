<template>
  <main class="app-shell">
    <section class="hero">
      <p class="eyebrow">Phase 1</p>
      <h1>Competency-based hiring MVP</h1>
      <p class="summary">
        This frontend now follows a standard Vite + Vue layout and is ready for
        the profile setup flows defined for the first project slice.
      </p>
    </section>
  </main>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem;
}

.hero {
  max-width: 40rem;
}

.eyebrow {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 1rem;
  font-size: clamp(2.5rem, 5vw, 4rem);
  line-height: 1.05;
}

.summary {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.6;
}
</style>
