    // Show text input for "Other" dream
    document.getElementById('other').addEventListener('change', function() {
        document.getElementById('other-dream').style.display = this.checked ? 'block' : 'none';
      });
      const canvas = document.getElementById('particle-canvas');
      const ctx = canvas.getContext('2d');
  
      let particles = [];
      const particleCount = 250;
      const maxRadius = 1.2;
      const maxOrbit = 15;
      const animationSpeed = 0.005;
  
      function Particle(x, y) {
          this.x = x;
          this.y = y;
          this.initialX = x;
          this.initialY = y;
          this.radius = Math.random() * maxRadius;
          this.angle = Math.random() * Math.PI * 2;
          this.orbitRadius = Math.random() * maxOrbit;
          this.color = 'rgba(255, 255, 255, ' + (0.3 + Math.random() * 0.5) + ')';
      }
  
      Particle.prototype.draw = function() {
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2, false);
          ctx.fillStyle = this.color;
          ctx.fill();
      };
  
      Particle.prototype.update = function() {
          this.angle += animationSpeed;
          this.x = this.initialX + Math.cos(this.angle) * this.orbitRadius;
          this.y = this.initialY + Math.sin(this.angle) * this.orbitRadius;
      };
  
      function init() {
          particles = [];
          canvas.width = window.innerWidth;
          canvas.height = window.innerHeight;
  
          for (let i = 0; i < particleCount; i++) {
              const x = Math.random() * canvas.width;
              const y = Math.random() * canvas.height;
              particles.push(new Particle(x, y));
          }
      }
  
      function animate() {
          requestAnimationFrame(animate);
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          particles.forEach(particle => {
              particle.update();
              particle.draw();
          });
      }
  
      window.addEventListener('resize', init);
      init();
      animate();