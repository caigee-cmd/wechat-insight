import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

import {
  buildRelationshipSphereModel,
  createSpherePoint,
} from "../lib/relationshipSphere";

function RelationshipSphereMap({ chatRows, contactRows, overview, social }) {
  const stageRef = useRef(null);
  const hoverRef = useRef(null);
  const lockRef = useRef(null);
  const syncHighlightsRef = useRef(() => {});
  const [lockedNodeId, setLockedNodeId] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);

  const model = useMemo(
    () =>
      buildRelationshipSphereModel({
        chatRows,
        contactRows,
        overview,
        social,
      }),
    [chatRows, contactRows, overview, social]
  );
  const nodeMap = useMemo(() => new Map(model.nodes.map((node) => [node.id, node])), [model.nodes]);
  const activeNode = hoveredNodeId ? nodeMap.get(hoveredNodeId) : nodeMap.get(lockedNodeId);
  const activeState = activeNode?.state || model.defaultState;

  useEffect(() => {
    hoverRef.current = hoveredNodeId;
    syncHighlightsRef.current();
  }, [hoveredNodeId]);

  useEffect(() => {
    lockRef.current = lockedNodeId;
    syncHighlightsRef.current();
  }, [lockedNodeId]);

  useEffect(() => {
    setHoveredNodeId(null);
    setLockedNodeId(null);
  }, [model.nodes]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage || !model.nodes.length) {
      return undefined;
    }

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    stage.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 30);
    camera.position.set(0, 0.16, 6.5);

    const ambient = new THREE.AmbientLight(0xf6f1e9, 1.12);
    const keyLight = new THREE.PointLight(0x9af0e2, 18, 30, 2);
    keyLight.position.set(4.8, 3.6, 5.4);
    const fillLight = new THREE.PointLight(0xffd38a, 14, 30, 2);
    fillLight.position.set(-5.4, -3.2, 4.2);
    const rimLight = new THREE.PointLight(0x8dc0dc, 9, 30, 2);
    rimLight.position.set(0, 0, -6.5);
    scene.add(ambient, keyLight, fillLight, rimLight);

    const globe = new THREE.Group();
    globe.position.y = 0.12;
    scene.add(globe);

    const shell = new THREE.Mesh(
      new THREE.SphereGeometry(model.radius * 0.98, 56, 56),
      new THREE.MeshPhongMaterial({
        color: 0x173b43,
        transparent: true,
        opacity: 0.08,
        side: THREE.DoubleSide,
        shininess: 80,
      })
    );
    globe.add(shell);

    const shellWire = new THREE.LineSegments(
      new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(model.radius * 1.01, 3)),
      new THREE.LineBasicMaterial({
        color: 0x74d9cc,
        transparent: true,
        opacity: 0.14,
      })
    );
    globe.add(shellWire);

    const equator = new THREE.Mesh(
      new THREE.TorusGeometry(model.radius * 0.92, 0.012, 10, 120),
      new THREE.MeshBasicMaterial({
        color: 0x2bd4bf,
        transparent: true,
        opacity: 0.18,
      })
    );
    equator.rotation.x = Math.PI / 2;
    globe.add(equator);

    const meridian = new THREE.Mesh(
      new THREE.TorusGeometry(model.radius * 0.82, 0.01, 10, 110),
      new THREE.MeshBasicMaterial({
        color: 0xe0a646,
        transparent: true,
        opacity: 0.14,
      })
    );
    meridian.rotation.y = Math.PI / 2.6;
    meridian.rotation.x = Math.PI / 2.15;
    globe.add(meridian);

    const dustCount = 180;
    const dustPositions = new Float32Array(dustCount * 3);
    const dustColors = new Float32Array(dustCount * 3);
    const dustColor = new THREE.Color();

    Array.from({ length: dustCount }).forEach((_, index) => {
      const band = index % 2 === 0 ? "group" : "contact";
      const point = createSpherePoint({
        band,
        count: dustCount,
        index,
        radius: model.radius * (1.03 + (index % 7) * 0.008),
      });
      dustPositions[index * 3] = point.x;
      dustPositions[index * 3 + 1] = point.y;
      dustPositions[index * 3 + 2] = point.z;
      dustColor.set(band === "group" ? 0x70e7d8 : 0xf6c36e);
      dustColors[index * 3] = dustColor.r;
      dustColors[index * 3 + 1] = dustColor.g;
      dustColors[index * 3 + 2] = dustColor.b;
    });

    const dustGeometry = new THREE.BufferGeometry();
    dustGeometry.setAttribute("position", new THREE.BufferAttribute(dustPositions, 3));
    dustGeometry.setAttribute("color", new THREE.BufferAttribute(dustColors, 3));
    const dust = new THREE.Points(
      dustGeometry,
      new THREE.PointsMaterial({
        size: 0.045,
        transparent: true,
        opacity: 0.72,
        vertexColors: true,
        depthWrite: false,
      })
    );
    globe.add(dust);

    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.56, 40, 40),
      new THREE.MeshStandardMaterial({
        color: 0x17313e,
        emissive: 0x0f766e,
        emissiveIntensity: 1.05,
        roughness: 0.28,
        metalness: 0.12,
      })
    );
    globe.add(core);

    const coreAura = new THREE.Mesh(
      new THREE.SphereGeometry(0.84, 28, 28),
      new THREE.MeshBasicMaterial({
        color: 0x2bd4bf,
        transparent: true,
        opacity: 0.08,
        depthWrite: false,
      })
    );
    globe.add(coreAura);

    const hitTargets = [];
    const nodeRecords = model.nodes.map((node) => {
      const anchor = new THREE.Group();
      anchor.position.set(node.position.x, node.position.y, node.position.z);

      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(node.color),
        emissive: new THREE.Color(node.color),
        emissiveIntensity: 0.54,
        roughness: 0.22,
        metalness: 0.08,
      });
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(node.size, 26, 26), material);
      mesh.userData.nodeId = node.id;
      hitTargets.push(mesh);
      anchor.add(mesh);

      const halo = new THREE.Mesh(
        new THREE.SphereGeometry(node.size * node.haloScale, 22, 22),
        new THREE.MeshBasicMaterial({
          color: new THREE.Color(node.color),
          transparent: true,
          opacity: 0.12,
          side: THREE.BackSide,
          depthWrite: false,
        })
      );
      anchor.add(halo);

      const spark = new THREE.Mesh(
        new THREE.SphereGeometry(node.size * 0.2, 12, 12),
        new THREE.MeshBasicMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.9,
        })
      );
      spark.position.z = node.size * 0.92;
      anchor.add(spark);

      globe.add(anchor);

      const nodeVector = new THREE.Vector3(node.position.x, node.position.y, node.position.z);
      const entryPoint = nodeVector.clone().multiplyScalar(0.22);
      const midPoint = nodeVector.clone().multiplyScalar(0.6);
      midPoint.y += node.curveLift;
      const curve = new THREE.CatmullRomCurve3([entryPoint, midPoint, nodeVector]);
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(28)),
        new THREE.LineBasicMaterial({
          color: new THREE.Color(node.lineColor),
          transparent: true,
          opacity: node.lineOpacity,
        })
      );
      globe.add(line);

      return {
        anchor,
        halo,
        line,
        material,
        mesh,
        node,
        spark,
      };
    });

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2(2, 2);
    const pointerTilt = { x: 0, y: 0 };
    const startedAt = performance.now();
    let frameId = 0;

    const syncHighlights = () => {
      const activeId = hoverRef.current || lockRef.current;
      nodeRecords.forEach((record) => {
        const isActive = record.node.id === activeId;
        const isMuted = Boolean(activeId) && !isActive;
        record.material.emissiveIntensity = isActive ? 1.35 : isMuted ? 0.32 : 0.56;
        record.halo.material.opacity = isActive ? 0.28 : isMuted ? 0.06 : 0.12;
        record.line.material.opacity = isActive
          ? Math.min(record.node.lineOpacity + 0.24, 1)
          : isMuted
            ? record.node.lineOpacity * 0.44
            : record.node.lineOpacity;
        record.anchor.scale.setScalar(isActive ? 1.18 : isMuted ? 0.96 : 1);
      });
      stage.style.cursor = hoverRef.current ? "pointer" : "default";
    };

    syncHighlightsRef.current = syncHighlights;
    syncHighlights();

    const resize = () => {
      const width = stage.clientWidth || 860;
      const height = stage.clientHeight || 560;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(stage);
    resize();

    const updateHoverFromPointer = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      pointerTilt.x = pointer.y * 0.2;
      pointerTilt.y = pointer.x * 0.32;

      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(hitTargets, false)[0];
      const nextId = hit?.object?.userData?.nodeId || null;
      if (hoverRef.current !== nextId) {
        hoverRef.current = nextId;
        setHoveredNodeId(nextId);
      }
    };

    const clearHover = () => {
      pointer.set(2, 2);
      pointerTilt.x = 0;
      pointerTilt.y = 0;
      if (hoverRef.current !== null) {
        hoverRef.current = null;
        setHoveredNodeId(null);
      }
    };

    const handleClick = () => {
      const hoveredId = hoverRef.current;
      setLockedNodeId((current) => (current === hoveredId ? null : hoveredId || null));
    };

    renderer.domElement.addEventListener("pointermove", updateHoverFromPointer);
    renderer.domElement.addEventListener("pointerleave", clearHover);
    renderer.domElement.addEventListener("click", handleClick);

    const renderFrame = () => {
      const elapsed = (performance.now() - startedAt) / 1000;
      globe.rotation.y = elapsed * 0.22;
      globe.rotation.x = THREE.MathUtils.lerp(globe.rotation.x, pointerTilt.x, 0.06);
      globe.rotation.z = THREE.MathUtils.lerp(globe.rotation.z, -pointerTilt.y * 0.38, 0.05);

      shell.rotation.y = elapsed * 0.08;
      shellWire.rotation.y = -elapsed * 0.12;
      equator.rotation.z = elapsed * 0.1;
      meridian.rotation.z = -elapsed * 0.08;
      core.scale.setScalar(1 + Math.sin(elapsed * 1.8) * 0.03);
      coreAura.scale.setScalar(1.02 + Math.sin(elapsed * 1.6) * 0.06);
      dust.rotation.y = elapsed * 0.04;

      nodeRecords.forEach((record) => {
        const pulse = 1 + Math.sin(elapsed * 1.4 + record.node.motionPhase) * 0.04;
        const activeId = hoverRef.current || lockRef.current;
        const isActive = record.node.id === activeId;
        record.halo.scale.setScalar((isActive ? 1.18 : 1) * pulse);
        record.spark.position.z = record.node.size * (0.92 + Math.sin(elapsed * 1.9 + record.node.motionPhase) * 0.08);
        record.spark.material.opacity = isActive ? 1 : 0.82;
      });

      renderer.render(scene, camera);
      frameId = window.requestAnimationFrame(renderFrame);
    };

    frameId = window.requestAnimationFrame(renderFrame);

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointermove", updateHoverFromPointer);
      renderer.domElement.removeEventListener("pointerleave", clearHover);
      renderer.domElement.removeEventListener("click", handleClick);
      syncHighlightsRef.current = () => {};
      nodeRecords.forEach((record) => {
        record.line.geometry.dispose();
        record.line.material.dispose();
        record.mesh.geometry.dispose();
        record.material.dispose();
        record.halo.geometry.dispose();
        record.halo.material.dispose();
        record.spark.geometry.dispose();
        record.spark.material.dispose();
      });
      shell.geometry.dispose();
      shell.material.dispose();
      shellWire.geometry.dispose();
      shellWire.material.dispose();
      equator.geometry.dispose();
      equator.material.dispose();
      meridian.geometry.dispose();
      meridian.material.dispose();
      dust.geometry.dispose();
      dust.material.dispose();
      core.geometry.dispose();
      core.material.dispose();
      coreAura.geometry.dispose();
      coreAura.material.dispose();
      renderer.dispose();
      stage.innerHTML = "";
    };
  }, [model]);

  if (!model.nodes.length) {
    return <div className="empty-state">暂无社交关系图数据</div>;
  }

  return (
    <div className="relationship-map relationship-map--sphere">
      <div className="relationship-map__hud">
        <span className="relationship-map__chip relationship-map__chip--group">群聊半球</span>
        <span className="relationship-map__chip relationship-map__chip--contact">私聊半球</span>
      </div>
      <div className="relationship-map__label relationship-map__label--top">高频群聊分布在上半球</div>
      <div className="relationship-map__label relationship-map__label--bottom">高频私聊分布在下半球</div>
      <div className="relationship-map__hint">移动指针微调视角，点击节点可锁定详情</div>
      <div aria-hidden="true" className="relationship-map__veil relationship-map__veil--top" />
      <div aria-hidden="true" className="relationship-map__veil relationship-map__veil--bottom" />
      <div className="relationship-map__stage" ref={stageRef} />

      <aside className={`relationship-inspector relationship-inspector--${activeState.theme}`}>
        <div className="relationship-inspector__eyebrow">{activeState.eyebrow}</div>
        <h3 className="relationship-inspector__title">{activeState.title}</h3>
        <div className="relationship-inspector__subtitle">{activeState.subtitle}</div>
        <p className="relationship-inspector__summary">{activeState.summary}</p>
        <div className="relationship-inspector__grid">
          <div className="relationship-inspector__metric">
            <span>节点类型</span>
            <strong>{activeState.type}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>消息量</span>
            <strong>{activeState.messages}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>商业</span>
            <strong>{activeState.business}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>售后/私聊</span>
            <strong>{activeState.support}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>活跃天数</span>
            <strong>{activeState.activeDays}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>自发占比</span>
            <strong>{activeState.selfRatio}</strong>
          </div>
        </div>
        <button className="relationship-inspector__reset" onClick={() => setLockedNodeId(null)} type="button">
          回到中心视角
        </button>
      </aside>
    </div>
  );
}

export default RelationshipSphereMap;
