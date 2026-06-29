<script>
	import "../app.css";
	import { Dumbbell } from "lucide-svelte";
	let { children } = $props();
</script>

<div class="app-wrapper">
	<nav class="glass-panel nav-header">
		<div class="container nav-content">
			<a href="/" class="brand">
				<span class="logo-icon"
					><Dumbbell size={28} color="var(--primary)" /></span
				>
				<span class="brand-text"
					>Pushup<span class="text-primary">Detection</span></span
				>
			</a>
			<div class="nav-links">
				<a href="/predict/image" class="nav-link">Image Analysis</a>
				<a href="/predict/realtime" class="nav-link"
					>Real-time Tracker</a
				>
				<a href="/history" class="nav-link">History</a>
			</div>
		</div>
	</nav>

	<main class="main-content">
		{@render children()}
	</main>

	<footer class="footer">
		<p>
			&copy; 2026 Pushup Posture Detection. Developed for Computer Vision
			UAS.
		</p>
	</footer>
</div>

<style>
	.app-wrapper {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	.nav-header {
		position: sticky;
		top: 0;
		z-index: 50;
		border-radius: 0;
		border-top: none;
		border-left: none;
		border-right: none;
	}

	.nav-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 2rem;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		color: var(--text-main);
	}

	.logo-icon {
		font-size: 1.5rem;
	}

	.brand-text {
		font-size: 1.5rem;
		font-weight: 700;
		letter-spacing: -0.5px;
	}

	.nav-links {
		display: flex;
		gap: 2rem;
	}

	.nav-link {
		color: var(--text-muted);
		text-decoration: none;
		font-weight: 500;
		transition: var(--transition);
		position: relative;
	}

	.nav-link:hover {
		color: var(--text-main);
	}

	.nav-link::after {
		content: "";
		position: absolute;
		bottom: -4px;
		left: 0;
		width: 0;
		height: 2px;
		background: var(--primary);
		transition: width 0.3s ease;
	}

	.nav-link:hover::after {
		width: 100%;
	}

	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.footer {
		text-align: center;
		padding: 2rem;
		color: var(--text-muted);
		font-size: 0.875rem;
		border-top: 1px solid var(--surface-border);
		margin-top: auto;
	}
</style>
