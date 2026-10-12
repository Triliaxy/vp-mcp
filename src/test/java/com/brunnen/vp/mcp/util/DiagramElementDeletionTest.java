package com.brunnen.vp.mcp.util;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.vp.plugin.diagram.IDiagramElement;
import com.vp.plugin.diagram.IDiagramUIModel;
import com.vp.plugin.diagram.IShapeUIModel;
import com.vp.plugin.model.IModelElement;
import com.vp.plugin.model.IProject;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class DiagramElementDeletionTest {
  private IDiagramUIModel diagram;
  private IShapeUIModel actor;
  private IModelElement model;
  private List<IDiagramElement> views;

  @BeforeEach
  public void setUp() {
    diagram = mock(IDiagramUIModel.class);
    actor = mock(IShapeUIModel.class);
    model = mock(IModelElement.class);
    when(actor.getId()).thenReturn("view-1");
    when(actor.getModelElement()).thenReturn(model);
    when(actor.getCustomText()).thenReturn("Actor caption");
    when(model.getId()).thenReturn("model-1");
    when(model.getName()).thenReturn("Test actor");
    views = new ArrayList<>(Arrays.asList(actor));
    when(diagram.diagramElementIterator())
        .thenAnswer(invocation -> new ArrayList<>(views).iterator());
  }

  @Test
  public void removesViewWithoutDeletingSharedModel() {
    doAnswer(
            invocation -> {
              views.remove(actor);
              return null;
            })
        .when(actor)
        .deleteViewOnly();
    DiagramElementDeletion.removeView(diagram, "Test actor");
    assertTrue(views.isEmpty());
    verify(model, never()).delete();
    verify(diagram, never()).removeDiagramElement(any());
  }

  @Test
  public void canFindShapeByCaption() {
    doAnswer(
            invocation -> {
              views.remove(actor);
              return null;
            })
        .when(actor)
        .deleteViewOnly();
    DiagramElementDeletion.removeView(diagram, "Actor caption");
    assertTrue(views.isEmpty());
  }

  @Test
  public void reportsFailureIfApiLeavesTheShapeAlive() {
    IllegalStateException error =
        assertThrows(
            IllegalStateException.class,
            () -> DiagramElementDeletion.removeView(diagram, "Test actor"));
    assertTrue(error.getMessage().contains("did not remove"));
    assertEquals(1, views.size());
  }

  @Test
  public void rejectsAmbiguousNamesWithoutDeletingAnything() {
    IShapeUIModel duplicate = mock(IShapeUIModel.class);
    when(duplicate.getModelElement()).thenReturn(model);
    views.add(duplicate);
    assertThrows(
        IllegalArgumentException.class,
        () -> DiagramElementDeletion.removeView(diagram, "Test actor"));
    verify(actor, never()).deleteViewOnly();
    verify(duplicate, never()).deleteViewOnly();
  }

  @Test
  public void rejectsMissingAndBlankNames() {
    assertThrows(
        IllegalArgumentException.class,
        () -> DiagramElementDeletion.removeView(diagram, "Unknown"));
    assertThrows(
        IllegalArgumentException.class, () -> DiagramElementDeletion.removeView(diagram, " "));
    verify(actor, never()).deleteViewOnly();
  }

  @Test
  public void deletesModelAndVerifiesAllItsViews() {
    IProject project = mock(IProject.class);
    IDiagramUIModel otherDiagram = mock(IDiagramUIModel.class);
    IDiagramElement otherView = mock(IDiagramElement.class);
    when(otherView.getId()).thenReturn("view-2");
    when(otherView.getModelElement()).thenReturn(model);
    List<IDiagramElement> otherViews = new ArrayList<>(Arrays.asList(otherView));
    List<IModelElement> models = new ArrayList<>(Arrays.asList(model));
    when(project.diagramIterator())
        .thenAnswer(invocation -> Arrays.asList(diagram, otherDiagram).iterator());
    when(project.allLevelModelElementIterator()).thenAnswer(invocation -> models.iterator());
    when(otherDiagram.diagramElementIterator()).thenAnswer(invocation -> otherViews.iterator());
    doAnswer(
            invocation -> {
              models.clear();
              views.clear();
              otherViews.clear();
              return null;
            })
        .when(model)
        .delete();
    DiagramElementDeletion.deleteModel(project, diagram, "Test actor");
    assertTrue(models.isEmpty());
    assertTrue(views.isEmpty());
    assertTrue(otherViews.isEmpty());
  }

  @Test
  public void detectsResidualViewAfterModelDeletion() {
    IProject project = mock(IProject.class);
    when(project.diagramIterator()).thenAnswer(invocation -> Arrays.asList(diagram).iterator());
    when(project.allLevelModelElementIterator())
        .thenAnswer(invocation -> new ArrayList<IModelElement>().iterator());
    assertThrows(
        IllegalStateException.class,
        () -> DiagramElementDeletion.deleteModel(project, diagram, "Test actor"));
  }
}
