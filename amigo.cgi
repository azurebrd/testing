#!/usr/bin/perl 

# test stuff about amigo

# test inferred dag view  2013 07 16

# ebi has a better graph in "Term Hierarchy"
# http://www.ebi.ac.uk/ontology-lookup/browse.do?ontName=GO&termId=GO%3A0033554&termName=cellular%20response%20to%20stress
# http://www.ebi.ac.uk/ontology-lookup/browse.do?ontName=GO&termId=GO:0034051&termName=cellular%20response%20to%20stress
#
# wormbase display 
# https://www.wormbase.org/species/all/go_term/GO:0033554#2--10
#
# berkeleybop display 
# http://amigo2.berkeleybop.org/cgi-bin/amigo2/amigo/term/GO:0033554
#
# berkeleybop json
# http://golr.berkeleybop.org/select?qt=standard&fl=*&version=2.2&wt=json&indent=on&rows=1&q=id:%22GO:0033554%22&fq=document_category:%22ontology_class%22
#
# graphviz documentation
# http://search.cpan.org/~rsavage/GraphViz-2.14/lib/GraphViz.pm
#
# using GraphViz to generate an SVG with clickable links to other nodes in the graph.
# using JSON to parse the json from berkeleybop
# using LWP::Simple to get json from berkeleybop
# given a goid, generate an svg graph with clickable nodes and make a separate table of children if there's too many.  for Raymond.  2013 07 17


use CGI;
use strict;
use LWP::Simple;
use JSON;
use GraphViz;

my $gviz = GraphViz->new(width=>6, height=>4);
my $json = JSON->new->allow_nonref;
my $query = new CGI;

&process();

sub process {
  my $action;                   # what user clicked
  unless ($action = $query->param('action')) { $action = 'none'; }

  if ($action eq 'Tree') { &dag(); }
    else { &dag(); }				# no action, show dag by default
} # sub process

sub getTopoHash {
  my ($goid) = @_;
  my $url = "http://golr.berkeleybop.org/select?qt=standard&fl=*&version=2.2&wt=json&indent=on&rows=1&q=id:%22" . $goid . "%22&fq=document_category:%22ontology_class%22";
  
  my $page_data = get $url;
  
  my $perl_scalar = $json->decode( $page_data );
  my %jsonHash = %$perl_scalar;

  my $topo_data = $json->decode( $jsonHash{"response"}{"docs"}[0]{"topology_graph_json"} );
  return $topo_data;
} # sub getTopoHash

sub dag {
  &printHtmlHeader(); 
  my ($var, $val) = &getHtmlVar($query, 'goid');

  my $goid = "GO:0033554";		# default goid if none given
  if ($val) { $goid = $val; }

  my ($topo_data) = &getTopoHash($goid);
  my %topo = %$topo_data;
  
  my %children; 			# children of the wanted goid, value is relationship type (predicate)
  my (@edges) = @{ $topo{"edges"} };
  for my $index (0 .. @edges) {
    my ($sub, $obj, $pred) = ('', '', '');
    if ($edges[$index]{'sub'}) { $sub = $edges[$index]{'sub'}; }
    if ($edges[$index]{'obj'}) { $obj = $edges[$index]{'obj'}; }
    if ($edges[$index]{'pred'}) { $pred = $edges[$index]{'pred'}; }
    if ($obj eq $goid) { $children{$sub} = $pred; }		# track children here
  }

  my $max_children = 5; my $child_table = ''; my $truncate_children = 0;
  if (scalar keys %children > $max_children) { $truncate_children++; }

  my %colorMap;
  $colorMap{"is_a"}                 = 'black';
  $colorMap{"part_of"}              = 'blue';
  $colorMap{"has_part"}             = 'purple';
  $colorMap{"regulates"}            = 'orange';
  $colorMap{"positively_regulates"} = 'green';
  $colorMap{"negatively_regulates"} = 'red';
  $colorMap{"occurs_in"}            = 'cyan';
  
  my (@edges) = @{ $topo{"edges"} };
  for my $index (0 .. @edges) {
    my ($sub, $obj, $pred) = ('', '', '');
    if ($edges[$index]{'sub'}) { $sub = $edges[$index]{'sub'}; }
    if ($edges[$index]{'obj'}) { $obj = $edges[$index]{'obj'}; }
    if ($edges[$index]{'pred'}) { $pred = $edges[$index]{'pred'}; }
    my $color = 'black'; if ($colorMap{$pred}) { $color = $colorMap{$pred}; }
    if ($sub && $obj && $pred) { 
      if ( ($children{$sub}) && $truncate_children) { next; }	# if too many children don't add edge for the child
      $gviz->add_edge("$obj" => "$sub", dir => "back", label => "$pred", color => "$color", fontcolor => "$color");
    } # if ($sub && $obj && $pred)
  } # for my $index (0 .. @edges)

  my %label;				# id to name
  my (@nodes) = @{ $topo{"nodes"} };
  for my $index (0 .. @nodes) {
    my ($id, $lbl) = ('', '');
    if ($nodes[$index]{'id'}) { $id = $nodes[$index]{'id'}; }
    if ($nodes[$index]{'lbl'}) { $lbl = $nodes[$index]{'lbl'}; }
    $label{$id} = $lbl;
    if ( ($children{$id}) && $truncate_children) { next; }	# if too many children don't add node for the child
    my $url = "amigo.cgi?action=Tree&goid=$id";
#     if ($id && $lbl) { $gviz->add_node("$id", label => "$id\n$lbl", color => "red", URL => "$url"); }	# have GOID and name in the node
    if ($id && $lbl) { $gviz->add_node("$id", label => "$lbl", color => "red", URL => "$url"); }
  }

  print qq(<embed width="200" height="100" type="image/svg+xml" src="whatsource.svg">\n);
  my $svgGenerated = $gviz->as_svg;
  my ($svgMarkup) = $svgGenerated =~ m/(<svg.*<\/svg>)/s;
  print qq($svgMarkup\n);
  print qq(</embed>\n);

  if ($truncate_children) {
    print "<br/><br/><br/>\n";
    $child_table .= "children : <br/>\n";
    $child_table .= qq(<table border="1"><tr><th>relationship</th><th>id</th><th>name</th></tr>\n);
    foreach my $child (sort keys %children) {
      my $relationship = $children{$child};
      my ($link_child) = &makeLink($child, $child);
      my $child_name = $label{$child};
      my ($link_childname) = &makeLink($child, $child_name);
      $child_table .= qq(<tr><td>$relationship</td><td>$link_child</td><td>$link_childname</td></tr>\n);
    } # foreach my $goid (sort keys %children)
    $child_table .= qq(</table>\n);
  }
  if ($child_table) { print $child_table; }

  &printHtmlFooter(); 
} # sub dag

sub makeLink {
  my ($goid, $text) = @_;
  my $url = "amigo.cgi?action=Tree&goid=$goid";
  my $link = qq(<a href="$url">$text</a>);
  return $link;
} # sub makeLink

sub printHtmlFooter { print qq(</body></html>\n); }

sub printHtmlHeader { print qq(Content-type: text/html\n\n<html><head><title>Amigo testing</title></head><body>\n); }

sub getHtmlVar {                
  no strict 'refs';             
  my ($query, $var, $err) = @_; 
  unless ($query->param("$var")) {
    if ($err) { print "<FONT COLOR=blue>ERROR : No such variable : $var</FONT><BR>\n"; }
  } else { 
    my $oop = $query->param("$var");
    $$var = &untaint($oop);         
    return ($var, $$var);           
  } 
} # sub getHtmlVar

sub untaint {
  my $tainted = shift;
  my $untainted;
  if ($tainted eq "") {
    $untainted = "";
  } else { # if ($tainted eq "")
    $tainted =~ s/[^\w\-.,;:?\/\\@#\$\%\^&*\>\<(){}[\]+=!~|' \t\n\r\f\"€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ]//g;
    if ($tainted =~ m/^([\w\-.,;:?\/\\@#\$\%&\^*\>\<(){}[\]+=!~|' \t\n\r\f\"€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ]+)$/) {
      $untainted = $1;
    } else {
      die "Bad data Tainted in $tainted";
    }
  } # else # if ($tainted eq "")
  return $untainted;
} # sub untaint

